"""Read stable releases and select only this product's platform assets."""
import json
import platform
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from app_paths import update_state_path as default_update_state_path
from app_version import CURRENT_VERSION

REPOSITORY = 'johnny05285514-code/oxford-to-notion'
RELEASES_BASE = f'https://github.com/{REPOSITORY}/releases'
RELEASES_API_URL = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
CHECK_INTERVAL = timedelta(hours=24)
MAX_PACKAGE_SIZE = 200_000_000
USER_AGENT = f'Oxford-to-Notion/{CURRENT_VERSION} (+personal low-frequency learning use)'


class UpdateCheckError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    version: str
    release_url: str
    package_url: str | None = None
    checksum_url: str | None = None
    filename: str | None = None
    size: int | None = None


def parse_version(value: object) -> tuple[int, int, int] | None:
    if not isinstance(value, str) or not re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value):
        return None
    return tuple(map(int, value.removeprefix('v').split('.')))


def platform_filename(version: str, system: str, machine: str) -> str | None:
    if system == 'win32' and machine.lower() in ('amd64', 'x86_64'):
        return f'Oxford-to-Notion-Setup-{version}.exe'
    if system == 'darwin' and machine.lower() in ('arm64', 'aarch64'):
        return 'Oxford-to-Notion-macOS-arm64.dmg'
    return None


def valid_download_info(info: UpdateInfo) -> bool:
    if parse_version(info.version) is None or info.version.startswith('v'):
        return False
    if info.release_url != f'{RELEASES_BASE}/tag/v{info.version}':
        return False
    names = (f'Oxford-to-Notion-Setup-{info.version}.exe', 'Oxford-to-Notion-macOS-arm64.dmg')
    base = f'{RELEASES_BASE}/download/v{info.version}/'
    return (info.filename in names and info.package_url == base + info.filename
            and info.checksum_url == base + info.filename + '.sha256'
            and type(info.size) is int and 0 < info.size <= MAX_PACKAGE_SIZE)


def _parse_release(payload: object, system: str, machine: str) -> UpdateInfo | None:
    if not isinstance(payload, dict):
        raise UpdateCheckError('Invalid release metadata')
    if payload.get('draft') is True or payload.get('prerelease') is True:
        return None
    version = parse_version(payload.get('tag_name'))
    if version is None or payload.get('draft') is not False or payload.get('prerelease') is not False:
        raise UpdateCheckError('Invalid release metadata')
    value = '.'.join(map(str, version))
    url = f'{RELEASES_BASE}/tag/v{value}'
    if payload.get('html_url') != url or payload.get('tag_name') != 'v'+value:
        raise UpdateCheckError('Invalid release URL')
    page = UpdateInfo(value, url)
    name = platform_filename(value, system, machine)
    assets = payload.get('assets')
    if not name or not isinstance(assets, list):
        return page
    package = [a for a in assets if isinstance(a, dict) and a.get('name') == name]
    checksum = [a for a in assets if isinstance(a, dict) and a.get('name') == name+'.sha256']
    if len(package) != 1 or len(checksum) != 1:
        return page
    info = UpdateInfo(value, url, package[0].get('browser_download_url'),
                      checksum[0].get('browser_download_url'), name, package[0].get('size'))
    return info if valid_download_info(info) else page


def _is_newer(info: UpdateInfo | None) -> UpdateInfo | None:
    return info if info and parse_version(info.version) > parse_version(CURRENT_VERSION) else None


def _read_cache(path: Path, system: str, machine: str):
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        if payload['schema'] != 2 or payload['platform'] != [system, machine]:
            return None
        timestamp = datetime.fromisoformat(payload['checked_at'])
        if timestamp.tzinfo is None:
            return None
        raw = payload['update']
        info = UpdateInfo(**raw) if isinstance(raw, dict) else None
        if raw is not None:
            if (info is None or parse_version(info.version) is None
                    or info.release_url != f'{RELEASES_BASE}/tag/v{info.version}'):
                return None
            if any(getattr(info, k) is not None for k in ('filename', 'size', 'package_url', 'checksum_url')):
                if not valid_download_info(info) or info.filename != platform_filename(info.version, system, machine):
                    return None
        return timestamp, info
    except (OSError, ValueError, TypeError, KeyError):
        return None


def _write_cache(path: Path, timestamp: datetime, info: UpdateInfo | None, system: str, machine: str):
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(dict(schema=2, platform=[system, machine], checked_at=timestamp.isoformat(),
                           update=asdict(info) if info else None), stream)
        temporary.replace(path)
    except OSError:
        pass
    finally:
        if temporary:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def check_for_update(*, session=None, state_path: Path | None = None,
                     now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                     force: bool = False, system: str | None = None,
                     machine: str | None = None) -> UpdateInfo | None:
    system, machine = system or sys.platform, machine or platform.machine()
    target, checked_now = state_path or default_update_state_path(), now()
    if checked_now.tzinfo is None:
        checked_now = checked_now.replace(tzinfo=timezone.utc)
    cached = _read_cache(target, system, machine)
    if not force and cached and timedelta(0) <= checked_now-cached[0] < CHECK_INTERVAL:
        return _is_newer(cached[1])
    client = session or requests.Session()
    try:
        response = client.get(RELEASES_API_URL, timeout=6, allow_redirects=False,
                              headers={'User-Agent': USER_AGENT, 'Accept': 'application/vnd.github+json'})
        try:
            if 300 <= getattr(response, 'status_code', 200) < 400:
                raise UpdateCheckError('Unexpected redirect')
            response.raise_for_status()
            info = _parse_release(response.json(), system, machine)
        finally:
            if hasattr(response, 'close'):
                response.close()
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise UpdateCheckError('Update check failed') from exc
    finally:
        if session is None:
            client.close()
    _write_cache(target, checked_now, info, system, machine)
    return _is_newer(info)

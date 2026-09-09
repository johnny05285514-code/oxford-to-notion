"""Stream and verify user-requested updates without accessing Notion settings."""
import hashlib
import re
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

from app_paths import updates_directory
from update_checker import MAX_PACKAGE_SIZE, USER_AGENT, UpdateInfo, valid_download_info


class UpdateDownloadError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def parse_checksum(text: str, filename: str) -> str:
    match = re.fullmatch(r'([a-fA-F0-9]{64}) [ *]' + re.escape(filename) + r'\r?\n?', text)
    if not match:
        raise UpdateDownloadError('integrity')
    return match[1].lower()


def cleanup_partial_downloads(cache_dir: Path) -> None:
    try:
        for path in cache_dir.glob('*/oton-*.part'):
            try:
                if not path.is_symlink() and time.time() - path.stat().st_mtime > 86400:
                    path.unlink()
            except OSError:
                pass
    except OSError:
        pass


def _redirect_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == 'https' and parsed.hostname == 'release-assets.githubusercontent.com'
                and parsed.port in (None, 443) and not parsed.username and not parsed.password)
    except ValueError:
        return False


def _get(client, url, guard):
    for _ in range(6):
        guard()
        response = client.get(url, stream=True, timeout=(10, 30), allow_redirects=False,
                              headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'})
        if response.status_code in (301, 302, 303, 307, 308):
            target = urljoin(url, response.headers.get('Location', ''))
            response.close()
            if not _redirect_url(target):
                raise UpdateDownloadError('network')
            url = target
            continue
        try:
            response.raise_for_status()
            if response.status_code != 200:
                raise UpdateDownloadError('network')
        except Exception:
            response.close()
            raise
        return response
    raise UpdateDownloadError('network')


def download_update(info: UpdateInfo, *, session=None, cache_dir: Path | None = None,
                    progress=None, cancelled=None) -> Path:
    if not valid_download_info(info):
        raise UpdateDownloadError('integrity')
    root = cache_dir if cache_dir is not None else updates_directory()
    client = session or requests.Session()
    if session is None:
        # Do not inherit netrc credentials for unrelated network operations.
        client.trust_env = False
    temporary = None
    deadline = time.monotonic() + 900

    def guard():
        if cancelled and cancelled():
            raise UpdateDownloadError('cancelled')
        if time.monotonic() > deadline:
            raise UpdateDownloadError('network')

    try:
        guard()
        folder = root / info.version
        folder.mkdir(parents=True, exist_ok=True)
        cleanup_partial_downloads(root)
        response = _get(client, info.checksum_url, guard)
        try:
            content = bytearray()
            for chunk in response.iter_content(chunk_size=4096):
                guard()
                content.extend(chunk)
                if len(content) > 16384:
                    raise UpdateDownloadError('integrity')
            expected = parse_checksum(content.decode('ascii'), info.filename)
        finally:
            response.close()
        destination = folder / info.filename
        if destination.is_file() and not destination.is_symlink() and destination.stat().st_size == info.size:
            digest = hashlib.sha256()
            with destination.open('rb') as stream:
                while chunk := stream.read(65536):
                    guard()
                    digest.update(chunk)
            if digest.hexdigest() == expected:
                if progress:
                    progress(info.size, info.size)
                return destination
        response = _get(client, info.package_url, guard)
        try:
            length = response.headers.get('Content-Length')
            if length is not None and (not length.isdigit() or int(length) != info.size):
                raise UpdateDownloadError('integrity')
            digest, received = hashlib.sha256(), 0
            with tempfile.NamedTemporaryFile(dir=folder, prefix='oton-', suffix='.part', delete=False) as stream:
                temporary = Path(stream.name)
                for chunk in response.iter_content(chunk_size=65536):
                    guard()
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > info.size or received > MAX_PACKAGE_SIZE:
                        raise UpdateDownloadError('size')
                    stream.write(chunk)
                    digest.update(chunk)
                    if progress:
                        progress(received, info.size)
            if received != info.size or digest.hexdigest() != expected:
                raise UpdateDownloadError('integrity')
            guard()
            temporary.replace(destination)
            return destination
        finally:
            response.close()
    except requests.RequestException as exc:
        raise UpdateDownloadError('network') from exc
    except UnicodeError as exc:
        raise UpdateDownloadError('integrity') from exc
    except OSError as exc:
        raise UpdateDownloadError('storage') from exc
    finally:
        if session is None:
            client.close()
        if temporary:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

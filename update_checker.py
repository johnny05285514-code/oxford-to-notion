import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from app_paths import update_state_path as default_update_state_path


CURRENT_VERSION = "1.4.0"
RELEASES_API_URL = (
    "https://api.github.com/repos/johnny05285514-code/oxford-to-notion/releases/latest"
)
CHECK_INTERVAL = timedelta(hours=24)
USER_AGENT = "Oxford-to-Notion/1.4.0 (+personal low-frequency learning use)"


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    version: str
    release_url: str


def parse_version(value: object) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized.startswith("v"):
        normalized = normalized[1:]
    parts = normalized.split(".")
    if not 1 <= len(parts) <= 3 or any(not part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    return tuple([*numbers, *([0] * (3 - len(numbers)))])  # type: ignore[return-value]


def _safe_https_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return value.strip()


def _parse_update(value: object) -> UpdateInfo | None:
    if not isinstance(value, dict):
        return None
    version_tuple = parse_version(value.get("version"))
    release_url = _safe_https_url(value.get("release_url"))
    if version_tuple is None or not release_url:
        return None
    return UpdateInfo(".".join(str(number) for number in version_tuple), release_url)


def _read_cache(path: Path) -> tuple[datetime, UpdateInfo | None] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        checked_at = datetime.fromisoformat(payload["checked_at"])
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    raw_update = payload.get("update")
    if raw_update is not None and _parse_update(raw_update) is None:
        return None
    return checked_at, _parse_update(raw_update)


def _write_cache(path: Path, checked_at: datetime, update: UpdateInfo | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    payload = {
        "checked_at": checked_at.isoformat(),
        "update": asdict(update) if update else None,
    }
    try:
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _is_newer(update: UpdateInfo | None) -> UpdateInfo | None:
    if update is None:
        return None
    candidate = parse_version(update.version)
    current = parse_version(CURRENT_VERSION)
    return update if candidate is not None and current is not None and candidate > current else None


def check_for_update(
    *,
    session: requests.Session | None = None,
    state_path: Path | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> UpdateInfo | None:
    target = state_path or default_update_state_path()
    checked_now = now()
    if checked_now.tzinfo is None:
        checked_now = checked_now.replace(tzinfo=timezone.utc)

    cached = _read_cache(target)
    if cached is not None:
        checked_at, cached_update = cached
        if checked_now - checked_at < CHECK_INTERVAL:
            return _is_newer(cached_update)

    client = session or requests.Session()
    try:
        response = client.get(
            RELEASES_API_URL,
            timeout=6,
            headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None

    update = None
    if not payload.get("draft") and not payload.get("prerelease"):
        version_tuple = parse_version(payload.get("tag_name"))
        release_url = _safe_https_url(payload.get("html_url"))
        if version_tuple is not None and release_url:
            update = UpdateInfo(
                ".".join(str(number) for number in version_tuple),
                release_url,
            )
    _write_cache(target, checked_now, _is_newer(update))
    return _is_newer(update)

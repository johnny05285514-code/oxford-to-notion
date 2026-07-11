import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from app_paths import history_path as default_history_path


MAX_HISTORY_ITEMS = 5


@dataclass(frozen=True, slots=True)
class ImportHistoryItem:
    word: str
    page_url: str
    imported_at: str


def _safe_web_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value.strip()


def _parse_item(value: object) -> ImportHistoryItem | None:
    if not isinstance(value, dict):
        return None
    word = value.get("word")
    page_url = _safe_web_url(value.get("page_url"))
    imported_at = value.get("imported_at")
    if not isinstance(word, str) or not word.strip() or not page_url:
        return None
    if not isinstance(imported_at, str):
        return None
    try:
        datetime.fromisoformat(imported_at)
    except ValueError:
        return None
    return ImportHistoryItem(word.strip().lower(), page_url, imported_at)


def read_history(path: Path | None = None) -> list[ImportHistoryItem]:
    target = path or default_history_path()
    if not target.exists():
        return []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        return []
    items = [item for raw in payload["items"] if (item := _parse_item(raw))]
    return items[:MAX_HISTORY_ITEMS]


def add_history_item(
    word: str,
    page_url: str,
    *,
    path: Path | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> list[ImportHistoryItem]:
    target = path or default_history_path()
    normalized_word = word.strip().lower()
    safe_url = _safe_web_url(page_url)
    if not normalized_word or not safe_url:
        return read_history(target)

    timestamp = now()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    newest = ImportHistoryItem(normalized_word, safe_url, timestamp.isoformat())
    existing = [item for item in read_history(target) if item.word != normalized_word]
    items = [newest, *existing][:MAX_HISTORY_ITEMS]

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    payload = {"items": [asdict(item) for item in items]}
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return items

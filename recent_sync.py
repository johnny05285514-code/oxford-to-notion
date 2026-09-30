from typing import Any

from import_service import build_dependencies
from history_store import ImportHistoryItem
from notion_writer import NotionWriter


def build_recent_reader() -> NotionWriter:
    # Worker-local connections keep imports and background reads isolated.
    return build_dependencies()[1]


def sync_recent_history(
    *,
    reader: Any | None = None,
) -> list[ImportHistoryItem]:
    active_reader = reader or build_recent_reader()
    # The UI persists only results that are still current when this read finishes.
    return active_reader.list_recent(limit=100)

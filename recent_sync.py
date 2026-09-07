from typing import Any

from notion_client import Client

from config import Settings
from history_store import ImportHistoryItem
from notion_writer import NotionWriter


def build_recent_reader() -> NotionWriter:
    settings = Settings.from_env()
    client = Client(auth=settings.notion_token)
    return NotionWriter(client, settings.notion_database_id)


def sync_recent_history(
    *,
    reader: Any | None = None,
) -> list[ImportHistoryItem]:
    active_reader = reader or build_recent_reader()
    # The UI persists only results that are still current when this read finishes.
    return active_reader.list_recent(limit=100)

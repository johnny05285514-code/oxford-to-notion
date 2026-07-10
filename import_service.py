from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from notion_client import Client

from config import Settings
from notion_writer import NotionWriter
from oxford_client import OxfordClient, normalize_word


@dataclass(frozen=True, slots=True)
class ImportResult:
    word: str
    page_url: str


def build_dependencies() -> tuple[OxfordClient, NotionWriter]:
    settings = Settings.from_env()
    notion_client = Client(auth=settings.notion_token)
    return OxfordClient(), NotionWriter(notion_client, settings.notion_database_id)


def import_word(
    word: str,
    *,
    oxford: Any | None = None,
    notion: Any | None = None,
    dependency_factory: Callable[[], tuple[Any, Any]] = build_dependencies,
) -> ImportResult:
    """Import one word and return the user-facing result."""
    if (oxford is None) != (notion is None):
        raise ValueError("Oxford and Notion dependencies must be provided together.")
    if oxford is None:
        oxford, notion = dependency_factory()

    normalized_word = normalize_word(word)
    entry = oxford.lookup(normalized_word)
    page_url = notion.upsert(entry)
    return ImportResult(word=entry.word, page_url=page_url)

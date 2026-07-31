from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from notion_client import Client

from config import Settings
from notion_writer import NotionWriter
from oxford_client import OxfordClient, normalize_word


@dataclass(frozen=True, slots=True)
class ImportTiming:
    oxford_seconds: float
    notion_check_seconds: float
    notion_write_seconds: float
    total_seconds: float


@dataclass(frozen=True, slots=True)
class ImportResult:
    word: str
    page_url: str
    oxford_url: str
    timing: ImportTiming | None = None


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
    clock: Callable[[], float] = perf_counter,
) -> ImportResult:
    """Import one word and return the user-facing result."""
    if (oxford is None) != (notion is None):
        raise ValueError("Oxford and Notion dependencies must be provided together.")
    if oxford is None:
        oxford, notion = dependency_factory()

    started_at = clock()
    normalized_word = normalize_word(word)
    entry = oxford.lookup(normalized_word)
    oxford_finished_at = clock()
    page_url = notion.upsert(entry)
    finished_at = clock()
    notion_timing = getattr(notion, "last_timing", None)
    notion_check_seconds = getattr(notion_timing, "check_seconds", 0.0)
    notion_write_seconds = getattr(
        notion_timing,
        "write_seconds",
        finished_at - oxford_finished_at,
    )
    return ImportResult(
        word=entry.word,
        page_url=page_url,
        oxford_url=entry.source_url,
        timing=ImportTiming(
            oxford_seconds=oxford_finished_at - started_at,
            notion_check_seconds=notion_check_seconds,
            notion_write_seconds=notion_write_seconds,
            total_seconds=finished_at - started_at,
        ),
    )

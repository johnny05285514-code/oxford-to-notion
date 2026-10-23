from collections.abc import Callable
from dataclasses import dataclass, replace
from time import perf_counter
from typing import Any
from threading import Lock
from contextlib import contextmanager

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
    cleanup_retry: Callable | None = None


class DependencyCache:
    """Own connections across Qt runnable callbacks, which lose thread locals."""

    def __init__(self):
        self.lock = Lock()
        self.key = None
        self.value = None

    @contextmanager
    def acquire(self):
        with self.lock:
            settings = Settings.from_env()
            key = (settings.notion_token, settings.notion_database_id)
            if self.key != key:
                if self.value is not None:
                    self.value[0].session.close()
                    self.value[1].client.close()
                self.value = None
                self.key = None
                self.value = (OxfordClient(), NotionWriter(
                    Client(auth=settings.notion_token), settings.notion_database_id,
                ))
                self.key = key
            yield self.value

    def import_word(self, word, progress=None):
        with self.acquire() as (oxford, notion):
            oxford.progress = notion.progress = progress or (lambda _stage, **_values: None)
            try:
                result = import_word(word, oxford=oxford, notion=notion)
            finally:
                oxford.progress = notion.progress = lambda _stage, **_values: None
            if notion.pending_cleanup:
                key = self.key
                pending = list(notion.pending_cleanup)
                def retry():
                    with self.acquire() as (_, writer):
                        if self.key != key:
                            raise ValueError("Notion settings changed. Restore the original settings before retrying cleanup.")
                        writer.pending_cleanup = list(pending)
                        writer.retry_cleanup()
                        pending[:] = writer.pending_cleanup
                        return replace(result, cleanup_retry=retry if pending else None)
                result = replace(result, cleanup_retry=retry)
            return result

    def list_recent(self):
        with self.acquire() as (_, notion):
            return notion.list_recent(limit=100)


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

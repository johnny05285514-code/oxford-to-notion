from collections.abc import Callable
from datetime import date
from typing import Any

import httpx
from notion_client.errors import APIResponseError, HTTPResponseError, RequestTimeoutError

from exceptions import NotionSchemaError, NotionWriteError
from models import WordEntry


RICH_TEXT_LIMIT = 2000
BLOCK_BATCH_SIZE = 100
MANAGED_BLOCK_TITLE = "Oxford content — managed by Oxford to Notion"
REQUIRED_SCHEMA = {
    "Name": "title",
    "Word": "rich_text",
    "Part of Speech": "select",
    "Countability": "rich_text",
    "Plural Form": "rich_text",
    "Definitions": "rich_text",
    "Examples": "rich_text",
    "Source URL": "url",
    "Added Date": "date",
}


def rich_text(text: str) -> list[dict[str, Any]]:
    return [
        {"type": "text", "text": {"content": text[index : index + RICH_TEXT_LIMIT]}}
        for index in range(0, len(text), RICH_TEXT_LIMIT)
    ]


def _text_block(block_type: str, text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": block_type,
        block_type: {"rich_text": rich_text(text)},
    }


def build_properties(entry: WordEntry, added_date: date | None = None) -> dict[str, Any]:
    labels = list(
        dict.fromkeys(label for definition in entry.definitions for label in definition.countability)
    )
    definitions = "\n".join(f"{item.number}. {item.text}" for item in entry.definitions)
    examples = "\n".join(
        f"{item.number}. {example}"
        for item in entry.definitions
        for example in item.examples
    )
    properties: dict[str, Any] = {
        "Name": {"title": rich_text(entry.word)},
        "Word": {"rich_text": rich_text(entry.word)},
        "Part of Speech": {"select": {"name": entry.part_of_speech}},
        "Countability": {"rich_text": rich_text(", ".join(labels))},
        "Plural Form": {"rich_text": rich_text(entry.plural_form or "")},
        "Definitions": {"rich_text": rich_text(definitions)},
        "Examples": {"rich_text": rich_text(examples)},
        "Source URL": {"url": entry.source_url},
    }
    if added_date is not None:
        properties["Added Date"] = {"date": {"start": added_date.isoformat()}}
    return properties


def build_blocks(entry: WordEntry) -> list[dict[str, Any]]:
    blocks = [_text_block("heading_1", f"{entry.word} {entry.part_of_speech}")]
    if entry.plural_form:
        blocks.append(_text_block("paragraph", f"Plural: {entry.plural_form}"))
    for item in entry.definitions:
        suffix = " ".join(item.countability)
        title = f"{item.number}." + (f" {suffix}" if suffix else "")
        blocks.append(_text_block("heading_2", title))
        blocks.append(_text_block("paragraph", item.text))
        blocks.extend(_text_block("bulleted_list_item", example) for example in item.examples)
    blocks.append(_text_block("paragraph", f"Source: {entry.source_url}"))
    return blocks


def build_managed_container() -> dict[str, Any]:
    """Return the marker block that owns only app-generated Oxford content."""
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {"rich_text": rich_text(MANAGED_BLOCK_TITLE)},
    }


class NotionWriter:
    def __init__(
        self,
        client: Any,
        database_id: str,
        today: Callable[[], date] = date.today,
    ) -> None:
        self.client = client
        self.database_id = database_id
        self.today = today

    def validate_connection(self) -> str:
        """Validate database access and schema without writing any data."""
        data_source_id, schema = self._resolve_data_source()
        self._validate_schema(schema)
        return data_source_id

    def upsert(self, entry: WordEntry) -> str:
        try:
            data_source_id, schema = self._resolve_data_source()
            self._validate_schema(schema)
            existing = self.client.data_sources.query(
                data_source_id=data_source_id,
                filter={"property": "Word", "rich_text": {"equals": entry.word}},
                page_size=1,
            ).get("results", [])
            blocks = build_blocks(entry)
            if existing:
                page = existing[0]
                old_managed_ids = self._managed_child_ids(page["id"])
                new_managed_id = self._append_managed_container(page["id"], blocks)
                updated = self.client.pages.update(
                    page_id=page["id"],
                    properties=build_properties(entry),
                )
                for block_id in old_managed_ids:
                    if block_id != new_managed_id:
                        self.client.blocks.delete(block_id=block_id)
                return updated.get("url") or page.get("url") or page["id"]

            page = self.client.pages.create(
                parent={"type": "data_source_id", "data_source_id": data_source_id},
                properties=build_properties(entry, self.today()),
            )
            try:
                self._append_managed_container(page["id"], blocks)
            except Exception:
                try:
                    self.client.pages.update(page_id=page["id"], archived=True)
                except Exception:
                    pass
                raise
            return page.get("url") or page["id"]
        except NotionSchemaError:
            raise
        except (
            APIResponseError,
            HTTPResponseError,
            RequestTimeoutError,
            httpx.RequestError,
            OSError,
        ) as exc:
            raise NotionWriteError("Notion API request failed. Check the token, database sharing, and permissions.") from exc

    def _resolve_data_source(self) -> tuple[str, dict[str, Any]]:
        database = self.client.databases.retrieve(database_id=self.database_id)
        sources = database.get("data_sources", [])
        if not sources:
            raise NotionSchemaError("The Notion database has no accessible data source.")
        data_source_id = sources[0]["id"]
        data_source = self.client.data_sources.retrieve(data_source_id=data_source_id)
        return data_source_id, data_source.get("properties", {})

    @staticmethod
    def _validate_schema(schema: dict[str, Any]) -> None:
        problems = []
        for name, expected_type in REQUIRED_SCHEMA.items():
            actual = schema.get(name, {}).get("type")
            if actual != expected_type:
                problems.append(f"{name} (expected {expected_type}, got {actual or 'missing'})")
        if problems:
            raise NotionSchemaError("Notion database schema mismatch: " + "; ".join(problems))

    def _list_children(self, block_id: str) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        cursor = None
        while True:
            kwargs = {"block_id": block_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor
            response = self.client.blocks.children.list(**kwargs)
            blocks.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
        return blocks

    @staticmethod
    def _block_text(block: dict[str, Any]) -> str:
        payload = block.get(block.get("type", ""), {})
        parts = []
        for item in payload.get("rich_text", []):
            parts.append(
                item.get("plain_text")
                or item.get("text", {}).get("content", "")
            )
        return "".join(parts).strip()

    def _managed_child_ids(self, page_id: str) -> list[str]:
        return [
            block["id"]
            for block in self._list_children(page_id)
            if block.get("type") == "toggle"
            and self._block_text(block) == MANAGED_BLOCK_TITLE
        ]

    def _append_managed_container(
        self, page_id: str, blocks: list[dict[str, Any]]
    ) -> str:
        response = self.client.blocks.children.append(
            block_id=page_id,
            children=[build_managed_container()],
        )
        results = response.get("results", [])
        if not results or not results[0].get("id"):
            raise NotionWriteError("Notion did not return the new managed content block.")
        managed_id = results[0]["id"]
        try:
            self._append_batches(managed_id, blocks)
        except Exception:
            try:
                self.client.blocks.delete(block_id=managed_id)
            except Exception:
                pass
            raise
        return managed_id

    def _append_batches(self, page_id: str, blocks: list[dict[str, Any]]) -> None:
        for index in range(0, len(blocks), BLOCK_BATCH_SIZE):
            self.client.blocks.children.append(
                block_id=page_id,
                children=blocks[index : index + BLOCK_BATCH_SIZE],
            )

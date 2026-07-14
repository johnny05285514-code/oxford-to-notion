from datetime import date

import pytest
import httpx
from notion_client.errors import RequestTimeoutError

from exceptions import NotionSchemaError, NotionWriteError
from models import Definition, WordEntry
from notion_writer import NotionWriter, build_blocks, build_properties, rich_text


ENTRY = WordEntry(
    word="brutality",
    part_of_speech="noun",
    plural_form="brutalities",
    definitions=(
        Definition(1, ("[uncountable]",), "violent and cruel behaviour", ("police brutality",)),
        Definition(2, ("[uncountable]",), "being direct about something unpleasant", ("the brutality of his words",)),
    ),
    source_url="https://example.test/brutality",
)


class Endpoint:
    def __init__(self, **responses):
        self.responses = responses
        self.calls = []

    def __getattr__(self, name):
        def call(**kwargs):
            self.calls.append((name, kwargs))
            response = self.responses.get(name, {})
            if isinstance(response, Exception):
                raise response
            return response(**kwargs) if callable(response) else response
        return call


class FakeClient:
    def __init__(self, query_results):
        self.databases = Endpoint(retrieve={"data_sources": [{"id": "data-source-id"}]})
        self.data_sources = Endpoint(
            retrieve={"properties": REQUIRED_SCHEMA},
            query={"results": query_results},
        )
        self.pages = Endpoint(create={"id": "new-page", "url": "https://notion/new"}, update={"url": "https://notion/existing"})
        self.blocks = Endpoint()
        self.blocks.children = Endpoint(list={"results": [], "has_more": False}, append={})


REQUIRED_SCHEMA = {
    "Name": {"type": "title"},
    "Word": {"type": "rich_text"},
    "Part of Speech": {"type": "select"},
    "Countability": {"type": "rich_text"},
    "Plural Form": {"type": "rich_text"},
    "Definitions": {"type": "rich_text"},
    "Examples": {"type": "rich_text"},
    "Source URL": {"type": "url"},
    "Added Date": {"type": "date"},
}


def test_rich_text_splits_long_content():
    result = rich_text("x" * 4001)

    assert [len(item["text"]["content"]) for item in result] == [2000, 2000, 1]


def test_build_properties_maps_entry_summary():
    props = build_properties(ENTRY, added_date=date(2026, 6, 21))

    assert props["Name"]["title"][0]["text"]["content"] == "brutality"
    assert props["Part of Speech"]["select"]["name"] == "noun"
    assert props["Plural Form"]["rich_text"][0]["text"]["content"] == "brutalities"
    assert props["Added Date"]["date"]["start"] == "2026-06-21"


def test_build_blocks_preserves_oxford_style_hierarchy():
    blocks = build_blocks(ENTRY)

    assert blocks[0]["type"] == "heading_1"
    assert blocks[0]["heading_1"]["rich_text"][0]["text"]["content"] == "brutality noun"
    assert any(block["type"] == "heading_2" for block in blocks)
    assert any(block["type"] == "bulleted_list_item" for block in blocks)


def test_schema_validation_reports_wrong_and_missing_fields():
    schema = dict(REQUIRED_SCHEMA)
    schema.pop("Plural Form")
    schema["Word"] = {"type": "url"}
    client = FakeClient([])
    client.data_sources = Endpoint(retrieve={"properties": schema}, query={"results": []})

    with pytest.raises(NotionSchemaError) as error:
        NotionWriter(client, "database-id").upsert(ENTRY)

    assert "Plural Form" in str(error.value)
    assert "Word" in str(error.value)


def test_upsert_creates_new_page():
    client = FakeClient([])
    _configure_managed_append(client)

    url = NotionWriter(client, "database-id", today=lambda: date(2026, 6, 21)).upsert(ENTRY)

    assert url == "https://notion/new"
    name, kwargs = client.pages.calls[-1]
    assert name == "create"
    assert kwargs["parent"] == {"type": "data_source_id", "data_source_id": "data-source-id"}
    assert "children" not in kwargs
    first_append = client.blocks.children.calls[0]
    assert first_append[1]["children"][0]["type"] == "toggle"


def test_upsert_updates_existing_page_without_deleting_unmanaged_children():
    client = FakeClient([{"id": "existing-page", "url": "https://notion/existing"}])
    client.blocks.children = Endpoint(
        list={"results": [{"id": "old-block"}], "has_more": False},
        append={},
    )
    client.blocks.delete = lambda **kwargs: client.blocks.calls.append(("delete", kwargs)) or {}
    _configure_managed_append(client)

    url = NotionWriter(client, "database-id").upsert(ENTRY)

    assert url == "https://notion/existing"
    assert ("delete", {"block_id": "old-block"}) not in client.blocks.calls
    assert client.blocks.children.calls[-1][0] == "append"
    update = next(kwargs for name, kwargs in client.pages.calls if name == "update")
    assert "Added Date" not in update["properties"]


def _paragraph(block_id, text):
    return {
        "id": block_id,
        "type": "paragraph",
        "paragraph": {"rich_text": [{"plain_text": text}]},
    }


def _managed_toggle(block_id):
    return {
        "id": block_id,
        "type": "toggle",
        "toggle": {
            "rich_text": [
                {"plain_text": "Oxford content — managed by Oxford to Notion"}
            ]
        },
    }


def _configure_managed_append(client, *, child_error=None):
    def append(**kwargs):
        if kwargs["block_id"] in {"existing-page", "new-page"}:
            return {"results": [{"id": "new-managed"}]}
        if child_error is not None:
            raise child_error
        return {"results": []}

    client.blocks.children.responses["append"] = append


def test_repeat_import_preserves_every_unmanaged_legacy_block():
    client = FakeClient([{"id": "existing-page", "url": "https://notion/existing"}])
    client.blocks.children = Endpoint(
        list={
            "results": [
                _paragraph("legacy-oxford", "brutality noun"),
                _paragraph("personal-note", "My own study note"),
            ],
            "has_more": False,
        },
        append={},
    )
    client.blocks.delete = lambda **kwargs: client.blocks.calls.append(("delete", kwargs)) or {}
    _configure_managed_append(client)

    NotionWriter(client, "database-id").upsert(ENTRY)

    deleted_ids = {
        kwargs["block_id"] for name, kwargs in client.blocks.calls if name == "delete"
    }
    assert "legacy-oxford" not in deleted_ids
    assert "personal-note" not in deleted_ids


def test_repeat_import_replaces_only_the_old_managed_container():
    client = FakeClient([{"id": "existing-page", "url": "https://notion/existing"}])
    client.blocks.children = Endpoint(
        list={
            "results": [
                _managed_toggle("old-managed"),
                _paragraph("personal-note", "Keep this note"),
            ],
            "has_more": False,
        },
        append={},
    )
    client.blocks.delete = lambda **kwargs: client.blocks.calls.append(("delete", kwargs)) or {}
    _configure_managed_append(client)

    NotionWriter(client, "database-id").upsert(ENTRY)

    deleted_ids = {
        kwargs["block_id"] for name, kwargs in client.blocks.calls if name == "delete"
    }
    assert deleted_ids == {"old-managed"}


def test_failed_replacement_keeps_old_managed_content():
    client = FakeClient([{"id": "existing-page", "url": "https://notion/existing"}])
    client.blocks.children = Endpoint(
        list={"results": [_managed_toggle("old-managed")], "has_more": False},
        append={},
    )
    client.blocks.delete = lambda **kwargs: client.blocks.calls.append(("delete", kwargs)) or {}
    _configure_managed_append(client, child_error=RequestTimeoutError())

    with pytest.raises(NotionWriteError):
        NotionWriter(client, "database-id").upsert(ENTRY)

    deleted_ids = [
        kwargs["block_id"] for name, kwargs in client.blocks.calls if name == "delete"
    ]
    assert "old-managed" not in deleted_ids


def test_upsert_wraps_httpx_transport_errors():
    request = httpx.Request("GET", "https://api.notion.com/v1/databases/test")
    client = FakeClient([])
    client.databases = Endpoint(
        retrieve=httpx.ConnectError("offline endpoint detail", request=request)
    )

    with pytest.raises(NotionWriteError, match="Notion API request failed") as error:
        NotionWriter(client, "database-id").upsert(ENTRY)

    assert "endpoint detail" not in str(error.value)

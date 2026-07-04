from datetime import date

import pytest

from exceptions import NotionSchemaError
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

    url = NotionWriter(client, "database-id", today=lambda: date(2026, 6, 21)).upsert(ENTRY)

    assert url == "https://notion/new"
    name, kwargs = client.pages.calls[-1]
    assert name == "create"
    assert kwargs["parent"] == {"type": "data_source_id", "data_source_id": "data-source-id"}
    assert kwargs["children"][0]["type"] == "heading_1"


def test_upsert_updates_existing_page_and_replaces_children():
    client = FakeClient([{"id": "existing-page", "url": "https://notion/existing"}])
    client.blocks.children = Endpoint(
        list={"results": [{"id": "old-block"}], "has_more": False},
        append={},
    )
    client.blocks.delete = lambda **kwargs: client.blocks.calls.append(("delete", kwargs)) or {}

    url = NotionWriter(client, "database-id").upsert(ENTRY)

    assert url == "https://notion/existing"
    assert ("delete", {"block_id": "old-block"}) in client.blocks.calls
    assert client.blocks.children.calls[-1][0] == "append"
    update = next(kwargs for name, kwargs in client.pages.calls if name == "update")
    assert "Added Date" not in update["properties"]

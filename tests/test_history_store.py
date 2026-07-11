import json
from datetime import datetime, timezone

from history_store import add_history_item, read_history


NOW = datetime(2026, 7, 12, 1, 2, 3, tzinfo=timezone.utc)


def test_missing_or_corrupt_history_is_empty(tmp_path):
    path = tmp_path / "history.json"
    assert read_history(path) == []

    path.write_text("not-json", encoding="utf-8")
    assert read_history(path) == []


def test_history_ignores_invalid_records_and_unsafe_urls(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "word": "valid",
                        "page_url": "https://www.notion.so/valid",
                        "imported_at": "2026-07-12T01:02:03+00:00",
                    },
                    {
                        "word": "unsafe",
                        "page_url": "file:///private.txt",
                        "imported_at": "2026-07-12T01:02:03+00:00",
                    },
                    {"word": "missing-fields"},
                    "not-a-record",
                ]
            }
        ),
        encoding="utf-8",
    )

    items = read_history(path)

    assert [item.word for item in items] == ["valid"]


def test_add_history_moves_duplicate_to_front_and_limits_to_five(tmp_path):
    path = tmp_path / "history.json"
    for index in range(6):
        add_history_item(
            f"word{index}",
            f"https://www.notion.so/word{index}",
            path=path,
            now=lambda: NOW,
        )

    items = add_history_item(
        "WORD3",
        "https://www.notion.so/word3-new",
        path=path,
        now=lambda: NOW,
    )

    assert [item.word for item in items] == ["word3", "word5", "word4", "word2", "word1"]
    assert items[0].page_url.endswith("word3-new")
    assert items[0].imported_at == "2026-07-12T01:02:03+00:00"


def test_add_history_writes_valid_json_without_leaving_temp_file(tmp_path):
    path = tmp_path / "nested" / "history.json"

    add_history_item(
        "brutality",
        "https://www.notion.so/brutality",
        path=path,
        now=lambda: NOW,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["items"][0]["word"] == "brutality"
    assert not path.with_suffix(".tmp").exists()


def test_add_history_rejects_unsafe_url_without_touching_file(tmp_path):
    path = tmp_path / "history.json"

    assert add_history_item("bad", "javascript:alert(1)", path=path) == []
    assert not path.exists()

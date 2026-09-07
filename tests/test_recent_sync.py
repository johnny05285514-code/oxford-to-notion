from history_store import ImportHistoryItem
from recent_sync import sync_recent_history


class FakeReader:
    def __init__(self, items):
        self.items = items
        self.limits = []

    def list_recent(self, limit=100):
        self.limits.append(limit)
        return self.items


def test_sync_recent_history_queries_one_hundred_without_writing_cache():
    items = [ImportHistoryItem("emit", "https://notion.so/emit", "2026-09-01")]
    reader = FakeReader(items)
    result = sync_recent_history(reader=reader)

    assert reader.limits == [100]
    assert result == items


def test_sync_recent_history_does_not_replace_cache_when_query_fails():
    class BrokenReader:
        def list_recent(self, limit=100):
            raise RuntimeError("offline")

    try:
        sync_recent_history(reader=BrokenReader())
    except RuntimeError as error:
        assert str(error) == "offline"
    else:
        raise AssertionError("sync should preserve and re-raise the query failure")

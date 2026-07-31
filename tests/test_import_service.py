from types import SimpleNamespace

import pytest

from import_service import ImportResult, import_word


class FakeOxford:
    def __init__(self, entry):
        self.entry = entry
        self.received_word = None

    def lookup(self, word):
        self.received_word = word
        return self.entry


class FakeNotion:
    def __init__(self):
        self.received_entry = None

    def upsert(self, entry):
        self.received_entry = entry
        return "https://notion.test/page"


def test_import_word_normalizes_and_returns_result():
    entry = SimpleNamespace(
        word="brutality",
        source_url=(
            "https://www.oxfordlearnersdictionaries.com/"
            "definition/english/brutality?q=brutality"
        ),
    )
    oxford = FakeOxford(entry)
    notion = FakeNotion()

    result = import_word("  Brutality  ", oxford=oxford, notion=notion)

    assert result.word == "brutality"
    assert result.page_url == "https://notion.test/page"
    assert getattr(result, "oxford_url", None) == entry.source_url
    assert oxford.received_word == "brutality"
    assert notion.received_entry is entry


def test_import_word_builds_dependencies_when_not_injected():
    entry = SimpleNamespace(
        word="brutality",
        source_url="https://www.oxfordlearnersdictionaries.com/definition/english/brutality",
    )
    oxford = FakeOxford(entry)
    notion = FakeNotion()
    calls = []

    def dependency_factory():
        calls.append(True)
        return oxford, notion

    result = import_word("brutality", dependency_factory=dependency_factory)

    assert result.word == "brutality"
    assert calls == [True]


def test_import_word_requires_dependencies_as_a_pair():
    entry = SimpleNamespace(word="brutality")

    with pytest.raises(ValueError, match="together"):
        import_word("brutality", oxford=FakeOxford(entry))


def test_import_word_returns_timing_breakdown():
    entry = SimpleNamespace(
        word="brutality",
        source_url="https://www.oxfordlearnersdictionaries.com/definition/english/brutality",
    )
    oxford = FakeOxford(entry)
    notion = FakeNotion()
    notion.last_timing = SimpleNamespace(check_seconds=0.3, write_seconds=0.7)
    ticks = iter((0.0, 0.5, 1.5))

    result = import_word(
        "brutality",
        oxford=oxford,
        notion=notion,
        clock=lambda: next(ticks),
    )

    assert result.timing.oxford_seconds == 0.5
    assert result.timing.notion_check_seconds == 0.3
    assert result.timing.notion_write_seconds == 0.7
    assert result.timing.total_seconds == 1.5

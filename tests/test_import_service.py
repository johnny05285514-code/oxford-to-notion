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
    entry = SimpleNamespace(word="brutality")
    oxford = FakeOxford(entry)
    notion = FakeNotion()

    result = import_word("  Brutality  ", oxford=oxford, notion=notion)

    assert result == ImportResult(word="brutality", page_url="https://notion.test/page")
    assert oxford.received_word == "brutality"
    assert notion.received_entry is entry


def test_import_word_builds_dependencies_when_not_injected():
    entry = SimpleNamespace(word="brutality")
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

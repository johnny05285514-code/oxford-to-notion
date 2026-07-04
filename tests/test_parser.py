from pathlib import Path

import pytest

from exceptions import OxfordStructureError
from parser import parse_entry


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_entry_preserves_senses_and_examples():
    html = (FIXTURES / "brutality_excerpt.html").read_text(encoding="utf-8")

    entry = parse_entry(html, "https://example.test/brutality")

    assert entry.word == "brutality"
    assert entry.part_of_speech == "noun"
    assert entry.plural_form == "brutalities"
    assert len(entry.definitions) == 2
    assert entry.definitions[0].number == 1
    assert entry.definitions[0].countability == ("[uncountable]",)
    assert entry.definitions[0].examples == (
        "police brutality",
        "the brutality of prison life",
        "the brutalities of war",
    )


def test_parse_entry_allows_missing_plural():
    html = """
    <div class='entry'><h1 class='headword'>kind</h1><span class='pos'>adjective</span>
      <li class='sense'><span class='def'>caring about others</span></li>
    </div>"""

    entry = parse_entry(html, "https://example.test/kind")

    assert entry.plural_form is None
    assert entry.definitions[0].countability == ()


def test_parse_entry_rejects_changed_structure():
    html = (FIXTURES / "invalid_page_excerpt.html").read_text(encoding="utf-8")

    with pytest.raises(OxfordStructureError, match="structure"):
        parse_entry(html, "https://example.test/broken")


def test_parse_entry_rejects_entry_without_definitions():
    html = "<div class='entry'><h1 class='headword'>empty</h1><span class='pos'>noun</span></div>"

    with pytest.raises(OxfordStructureError, match="definition"):
        parse_entry(html, "https://example.test/empty")

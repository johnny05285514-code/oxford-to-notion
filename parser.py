from bs4 import BeautifulSoup, Tag

from exceptions import OxfordStructureError
from models import Definition, WordEntry


# Oxford-specific selectors live here so a layout change has one maintenance point.
SELECTORS = {
    "entry": ("div.entry", "div.entry_container"),
    "word": (".headword", "h1"),
    "part_of_speech": (".pos",),
    "plural": (".inflections .inflected_form", ".inflected_form"),
    "sense": ("li.sense",),
    "definition": (".def",),
    "countability": (".grammar", ".gram"),
    "example": (".examples .x", "ul.examples li"),
}


def _first(root: Tag | BeautifulSoup, selectors: tuple[str, ...]) -> Tag | None:
    for selector in selectors:
        node = root.select_one(selector)
        if node is not None:
            return node
    return None


def _clean(node: Tag | None) -> str:
    return node.get_text(" ", strip=True) if node else ""


def _normalize_label(value: str) -> str:
    value = " ".join(value.split())
    if value and not value.startswith("["):
        return f"[{value.strip('[]')}]"
    return value


def parse_entry(html: str, source_url: str) -> WordEntry:
    soup = BeautifulSoup(html, "html.parser")
    entry = _first(soup, SELECTORS["entry"])
    if entry is None:
        raise OxfordStructureError("Oxford page structure was not recognized (entry missing).")

    word = _clean(_first(entry, SELECTORS["word"]))
    part_of_speech = _clean(_first(entry, SELECTORS["part_of_speech"]))
    if not word or not part_of_speech:
        raise OxfordStructureError("Oxford page structure was not recognized (headword or part of speech missing).")

    plural = _clean(_first(entry, SELECTORS["plural"])) or None
    definitions: list[Definition] = []
    for sense in entry.select(", ".join(SELECTORS["sense"])):
        definition_text = _clean(_first(sense, SELECTORS["definition"]))
        if not definition_text:
            continue
        labels = tuple(
            dict.fromkeys(
                label
                for label in (
                    _normalize_label(_clean(node))
                    for selector in SELECTORS["countability"]
                    for node in sense.select(selector)
                )
                if label
            )
        )
        examples: list[str] = []
        for selector in SELECTORS["example"]:
            found = [_clean(node) for node in sense.select(selector)]
            if found:
                examples = list(dict.fromkeys(text for text in found if text))
                break
        definitions.append(
            Definition(
                number=len(definitions) + 1,
                countability=labels,
                text=definition_text,
                examples=tuple(examples),
            )
        )

    if not definitions:
        raise OxfordStructureError("Oxford page structure was not recognized (definition missing).")

    return WordEntry(
        word=word,
        part_of_speech=part_of_speech,
        plural_form=plural,
        definitions=tuple(definitions),
        source_url=source_url,
    )

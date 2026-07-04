from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Definition:
    number: int
    countability: tuple[str, ...]
    text: str
    examples: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WordEntry:
    word: str
    part_of_speech: str
    plural_form: str | None
    definitions: tuple[Definition, ...]
    source_url: str

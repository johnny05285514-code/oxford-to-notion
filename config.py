import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv

from exceptions import ConfigurationError


NOTION_ID_PATTERN = re.compile(
    r"([0-9a-fA-F]{32}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)


def normalize_notion_database_id(value: str) -> str:
    """Accept either a Notion database ID or a Notion database URL."""
    compact_value = value.strip()
    match = NOTION_ID_PATTERN.search(compact_value)
    return match.group(1).replace("-", "") if match else compact_value


@dataclass(frozen=True, slots=True)
class Settings:
    notion_token: str
    notion_database_id: str

    @classmethod
    def from_env(cls, load_file: bool = True) -> "Settings":
        if load_file:
            load_dotenv()
        values = {
            "NOTION_TOKEN": os.getenv("NOTION_TOKEN", "").strip(),
            "NOTION_DATABASE_ID": os.getenv("NOTION_DATABASE_ID", "").strip(),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ConfigurationError("Missing required environment variables: " + ", ".join(missing))
        return cls(values["NOTION_TOKEN"], normalize_notion_database_id(values["NOTION_DATABASE_ID"]))

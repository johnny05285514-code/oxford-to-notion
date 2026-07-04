import os
from dataclasses import dataclass

from dotenv import load_dotenv

from exceptions import ConfigurationError


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
        return cls(values["NOTION_TOKEN"], values["NOTION_DATABASE_ID"])

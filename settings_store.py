import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, set_key

from app_paths import env_path as default_env_path
from exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class StoredNotionSettings:
    notion_token: str
    notion_database_value: str

    @property
    def is_complete(self) -> bool:
        return bool(self.notion_token and self.notion_database_value)


def read_notion_settings(*, env_path: Path | None = None) -> StoredNotionSettings:
    path = env_path or default_env_path()
    values = dotenv_values(path) if path.exists() else {}
    return StoredNotionSettings(
        notion_token=(values.get("NOTION_TOKEN") or "").strip(),
        notion_database_value=(values.get("NOTION_DATABASE_ID") or "").strip(),
    )


def save_notion_settings(
    notion_token: str,
    notion_database_value: str,
    *,
    env_path: Path | None = None,
) -> None:
    token = notion_token.strip()
    database = notion_database_value.strip()
    missing = []
    if not token:
        missing.append("NOTION_TOKEN")
    if not database:
        missing.append("NOTION_DATABASE_ID")
    if missing:
        raise ConfigurationError("Missing required settings: " + ", ".join(missing))

    path = env_path or default_env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    set_key(str(path), "NOTION_TOKEN", token)
    set_key(str(path), "NOTION_DATABASE_ID", database)

    # Keep the running GUI in sync without requiring a restart.
    os.environ["NOTION_TOKEN"] = token
    os.environ["NOTION_DATABASE_ID"] = database

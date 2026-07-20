import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, set_key

from app_paths import env_path as default_env_path
from exceptions import ConfigurationError
from i18n import SUPPORTED_LANGUAGE_CODES


HISTORY_LINK_TARGET_NOTION = "notion"
HISTORY_LINK_TARGET_OXFORD = "oxford"
HISTORY_LINK_TARGETS = {
    HISTORY_LINK_TARGET_NOTION,
    HISTORY_LINK_TARGET_OXFORD,
}


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


def read_app_language(*, env_path: Path | None = None) -> str | None:
    path = env_path or default_env_path()
    values = dotenv_values(path) if path.exists() else {}
    language = (values.get("APP_LANGUAGE") or "").strip()
    return language if language in SUPPORTED_LANGUAGE_CODES else None


def save_app_language(language: str, *, env_path: Path | None = None) -> None:
    if language not in SUPPORTED_LANGUAGE_CODES:
        raise ConfigurationError(f"Unsupported application language: {language}")

    path = env_path or default_env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    set_key(str(path), "APP_LANGUAGE", language)


def read_history_link_target(*, env_path: Path | None = None) -> str:
    path = env_path or default_env_path()
    values = dotenv_values(path) if path.exists() else {}
    target = (values.get("HISTORY_LINK_TARGET") or "").strip().lower()
    return target if target in HISTORY_LINK_TARGETS else HISTORY_LINK_TARGET_NOTION


def save_history_link_target(
    target: str,
    *,
    env_path: Path | None = None,
) -> None:
    normalized = target.strip().lower()
    if normalized not in HISTORY_LINK_TARGETS:
        raise ConfigurationError(f"Unsupported history link target: {target}")

    path = env_path or default_env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    set_key(str(path), "HISTORY_LINK_TARGET", normalized)

from pathlib import Path

import pytest
from dotenv import dotenv_values

from exceptions import ConfigurationError
from settings_store import (
    HISTORY_LINK_TARGET_NOTION,
    HISTORY_LINK_TARGET_OXFORD,
    read_history_link_target,
    read_notion_settings,
    save_history_link_target,
    save_notion_settings,
)


def test_save_and_read_notion_settings(tmp_path: Path):
    env_path = tmp_path / ".env"

    save_notion_settings(
        "test_token",
        "https://www.notion.so/workspace/Vocabulary-11111111222233334444555555555555",
        env_path=env_path,
    )

    saved = read_notion_settings(env_path=env_path)
    assert saved.notion_token == "test_token"
    assert "11111111222233334444555555555555" in saved.notion_database_value


def test_save_preserves_unrelated_env_values(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text("UNRELATED=keep-me\n", encoding="utf-8")

    save_notion_settings("test_token", "test_database", env_path=env_path)

    assert "UNRELATED=keep-me" in env_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("token", "database", "missing_name"),
    [
        ("", "database", "NOTION_TOKEN"),
        ("token", "", "NOTION_DATABASE_ID"),
    ],
)
def test_save_rejects_missing_values(tmp_path: Path, token, database, missing_name):
    with pytest.raises(ConfigurationError, match=missing_name):
        save_notion_settings(token, database, env_path=tmp_path / ".env")


def test_history_link_target_defaults_to_notion(tmp_path: Path):
    assert (
        read_history_link_target(env_path=tmp_path / ".env")
        == HISTORY_LINK_TARGET_NOTION
    )


def test_history_link_target_round_trips_and_preserves_credentials(tmp_path: Path):
    path = tmp_path / ".env"
    path.write_text(
        "NOTION_TOKEN=secret-value\nNOTION_DATABASE_ID=database-value\n",
        encoding="utf-8",
    )

    save_history_link_target(HISTORY_LINK_TARGET_OXFORD, env_path=path)

    assert read_history_link_target(env_path=path) == HISTORY_LINK_TARGET_OXFORD
    values = dotenv_values(path)
    assert values["NOTION_TOKEN"] == "secret-value"
    assert values["NOTION_DATABASE_ID"] == "database-value"


def test_invalid_saved_history_link_target_falls_back_to_notion(tmp_path: Path):
    path = tmp_path / ".env"
    path.write_text("HISTORY_LINK_TARGET=unknown\n", encoding="utf-8")

    assert read_history_link_target(env_path=path) == HISTORY_LINK_TARGET_NOTION


def test_rejects_invalid_history_link_target(tmp_path: Path):
    with pytest.raises(ConfigurationError, match="Unsupported history link target"):
        save_history_link_target("unknown", env_path=tmp_path / ".env")

from pathlib import Path

import pytest

from exceptions import ConfigurationError
from settings_store import read_notion_settings, save_notion_settings


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

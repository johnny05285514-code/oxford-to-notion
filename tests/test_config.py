import pytest

from config import Settings
from exceptions import ConfigurationError


def test_settings_reads_required_environment(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "test_notion_token")
    monkeypatch.setenv("NOTION_DATABASE_ID", "test_database_id")

    settings = Settings.from_env(load_file=False)

    assert settings.notion_token == "test_notion_token"
    assert settings.notion_database_id == "test_database_id"


def test_settings_lists_missing_values(monkeypatch):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

    with pytest.raises(ConfigurationError, match="NOTION_TOKEN.*NOTION_DATABASE_ID"):
        Settings.from_env(load_file=False)

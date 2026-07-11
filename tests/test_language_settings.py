from dotenv import dotenv_values

from settings_store import read_app_language, save_app_language


def test_read_language_accepts_supported_value(tmp_path):
    path = tmp_path / ".env"
    path.write_text("APP_LANGUAGE=zh-CN\n", encoding="utf-8")

    assert read_app_language(env_path=path) == "zh-CN"


def test_read_language_ignores_unsupported_value(tmp_path):
    path = tmp_path / ".env"
    path.write_text("APP_LANGUAGE=fr\n", encoding="utf-8")

    assert read_app_language(env_path=path) is None


def test_save_language_preserves_notion_settings(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "NOTION_TOKEN=secret-value\nNOTION_DATABASE_ID=database-value\n",
        encoding="utf-8",
    )

    save_app_language("en", env_path=path)
    values = dotenv_values(path)

    assert values["APP_LANGUAGE"] == "en"
    assert values["NOTION_TOKEN"] == "secret-value"
    assert values["NOTION_DATABASE_ID"] == "database-value"

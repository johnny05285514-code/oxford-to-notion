import pytest

from i18n import Translator, localize_error


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "Oxford request failed after retrying.",
            "Cannot connect to Oxford. Check your internet connection and try again.",
        ),
        (
            "Oxford has no entry for 'madeupword'.",
            "Oxford could not find “madeupword”. Check the spelling and try again.",
        ),
        (
            "Notion Token 无效或已失效",
            "The Notion Token is invalid or has expired. Copy the Integration Token again.",
        ),
        (
            "找不到这个数据库。请确认已把 Integration 连接到这个数据库。",
            "Notion denied access. Make sure your Integration is connected to this database.",
        ),
        (
            "数据库字段不符合要求: Missing Examples",
            "The database is missing the “Examples” property. Copy the template again or add that property.",
        ),
    ],
)
def test_errors_are_friendly_in_english(raw, expected):
    assert localize_error(raw, Translator("en")) == expected


def test_errors_are_friendly_in_chinese():
    assert localize_error("Oxford request failed.", Translator("zh-CN")) == (
        "无法连接 Oxford，请检查网络后重试。"
    )
    assert localize_error(
        "找不到这个数据库。请确认已把 Integration 连接到这个数据库。",
        Translator("zh-CN"),
    ) == "Notion 拒绝访问。请确认 Integration 已连接到这个数据库。"


def test_unknown_error_uses_safe_generic_message():
    assert localize_error("secret transport details", Translator("en")) == (
        "Something unexpected happened. Please try again."
    )

from i18n import Translator, detect_system_language


def test_chinese_locale_selects_simplified_chinese():
    assert detect_system_language("zh_CN") == "zh-CN"
    assert detect_system_language("zh-Hans-CN") == "zh-CN"


def test_unknown_or_missing_locale_selects_english():
    assert detect_system_language("fr_FR") == "en"
    assert detect_system_language("") == "en"


def test_translator_formats_values():
    translator = Translator("en", catalogs={"en": {"querying": "Looking up {word}…"}})

    assert translator.text("querying", word="brutality") == "Looking up brutality…"


def test_missing_chinese_translation_falls_back_to_english():
    translator = Translator(
        "zh-CN",
        catalogs={"en": {"only_english": "English fallback"}, "zh-CN": {}},
    )

    assert translator.text("only_english") == "English fallback"


def test_unknown_language_is_normalized_to_english():
    assert Translator("es").language == "en"

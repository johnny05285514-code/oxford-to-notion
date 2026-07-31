import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import gui
from gui import OxfordToNotionWindow
from settings_store import StoredNotionSettings


def make_window(monkeypatch, *, saved_language="zh-CN"):
    app = QApplication.instance() or QApplication([])
    app.setFont(gui.build_ui_font())
    monkeypatch.setattr(
        gui,
        "read_notion_settings",
        lambda: StoredNotionSettings("token", "database"),
    )
    monkeypatch.setattr(gui, "read_app_language", lambda: saved_language)
    monkeypatch.setattr(gui, "read_history_link_target", lambda: "notion")
    monkeypatch.setattr(gui, "save_history_link_target", lambda _target: None)
    saved = []
    monkeypatch.setattr(gui, "save_app_language", saved.append)
    return app, OxfordToNotionWindow(), saved


def test_saved_language_is_used_and_menu_is_extensible(monkeypatch):
    _app, window, _saved = make_window(monkeypatch, saved_language="en")

    assert window.language == "en"
    assert window.language_button.text() == ""
    assert not window.language_button.icon().isNull()
    assert window.language_button.toolTip() == "Language"
    assert [action.text() for action in window.language_menu.actions()] == [
        "简体中文",
        "English",
    ]
    assert [action.isCheckable() for action in window.language_menu.actions()] == [True, True]
    assert [action.isChecked() for action in window.language_menu.actions()] == [False, True]
    assert window.language_button.width() == 46
    assert window.settings_button is window.nav_settings_button
    assert window.nav_import_button.text() == "Import"
    assert window.nav_recent_button.text() == "Recent"

    window.close()


def test_switching_language_retranslates_main_and_settings_pages(monkeypatch):
    _app, window, saved = make_window(monkeypatch)

    window.set_language("en")

    assert window.settings_button.text() == "Settings"
    assert window.import_button.text() == "Import to Notion"
    assert window.language_button.toolTip() == "Language"
    assert window.settings_title_label.text() == "Notion Settings"
    assert window.settings_save_button.text() == "Save settings"
    assert window.history_target_label.text() == "Open recent imports in"
    assert window.performance_diagnostics_checkbox.text() == "Show import performance details"
    assert [window.history_target_combo.itemText(index) for index in range(2)] == [
        "Notion",
        "Oxford Learner's Dictionaries",
    ]
    assert saved == ["en"]

    window.set_language("zh-CN")
    assert window.settings_button.text() == "设置"
    assert window.import_button.text() == "导入到 Notion"
    assert window.language_button.toolTip() == "切换语言"
    assert window.history_target_label.text() == "最近导入打开方式"
    assert window.performance_diagnostics_checkbox.text() == "显示导入性能详情"
    assert [window.history_target_combo.itemText(index) for index in range(2)] == [
        "Notion",
        "Oxford Learner's Dictionaries",
    ]
    assert saved == ["en", "zh-CN"]

    window.close()


def test_missing_saved_language_uses_detected_system_language(monkeypatch):
    monkeypatch.setattr(gui, "detect_system_language", lambda: "en")
    _app, window, _saved = make_window(monkeypatch, saved_language=None)

    assert window.language == "en"
    assert window.subtitle_label.text().startswith("Enter an English word")

    window.close()


def test_settings_page_scrolls_instead_of_compressing_groups(monkeypatch):
    app, window, _saved = make_window(monkeypatch, saved_language="en")
    window.show()
    app.processEvents()
    window.resize(window.minimumSize())
    window.show_settings_page()
    app.processEvents()

    assert hasattr(window, "settings_scroll")
    assert window.settings_scroll.verticalScrollBar().maximum() > 0
    assert window.settings_content.width() <= window.settings_scroll.viewport().width()
    window.close()

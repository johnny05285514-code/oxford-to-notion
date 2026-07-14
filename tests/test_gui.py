import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import gui
from gui import OxfordToNotionWindow, SuccessIcon, build_ui_font
from settings_store import StoredNotionSettings


class HoldingThreadPool:
    def __init__(self):
        self.worker = None

    def start(self, worker):
        self.worker = worker


def test_ui_font_has_explicit_latin_and_chinese_families():
    font = build_ui_font()

    assert font.families()[:2] == ["Segoe UI", "Microsoft YaHei UI"]
    assert font.pointSize() == 10
    assert font.hintingPreference() == font.HintingPreference.PreferVerticalHinting


def test_success_icon_is_a_fixed_vector_widget():
    app = QApplication.instance() or QApplication([])
    icon = SuccessIcon()

    assert icon.sizeHint().width() == 20
    assert icon.sizeHint().height() == 20
    assert icon.width() == 20
    assert icon.height() == 20

    icon.close()
    assert app is not None


def test_first_launch_opens_setup_wizard(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        gui,
        "read_notion_settings",
        lambda: StoredNotionSettings("", ""),
    )

    window = OxfordToNotionWindow(start_update_check=False)

    assert window.stack.currentWidget() is window.wizard_page
    window.close()
    assert app is not None


def test_existing_configuration_opens_main_page(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        gui,
        "read_notion_settings",
        lambda: StoredNotionSettings("token", "database"),
    )

    window = OxfordToNotionWindow(start_update_check=False)

    assert window.stack.currentWidget() is window.main_page
    window.close()
    assert app is not None


def test_settings_does_not_show_success_for_credentials_edited_during_test(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        gui,
        "read_notion_settings",
        lambda: StoredNotionSettings("token", "database"),
    )
    window = OxfordToNotionWindow(start_update_check=False)
    pool = HoldingThreadPool()
    window.thread_pool = pool
    window.show_settings_page()
    window.token_entry.setText("tested-token")
    window.database_entry.setText("tested-database")
    window.start_settings_connection_test()

    window.database_entry.setText("edited-database")
    window.finish_settings_connection_test(None)

    assert window._settings_status_key != "connection_success"
    assert pool.worker is not None
    window.close()
    assert app is not None

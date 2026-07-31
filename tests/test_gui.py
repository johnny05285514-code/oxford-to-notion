import os
from types import SimpleNamespace

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


def test_performance_checkbox_uses_high_contrast_blue_checkmark(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        gui,
        "read_notion_settings",
        lambda: StoredNotionSettings("token", "database"),
    )
    window = OxfordToNotionWindow(start_update_check=False)
    checkbox = window.performance_diagnostics_checkbox
    checkbox.setChecked(True)
    checkbox.show()
    app.processEvents()

    image = checkbox.grab().toImage()
    colors = {
        image.pixelColor(x, y).name()
        for x in range(min(24, image.width()))
        for y in range(image.height())
    }

    assert "#1769e8" in colors
    assert "#ffffff" in colors
    window.close()


def test_history_target_combo_uses_soft_vector_chevron(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        gui,
        "read_notion_settings",
        lambda: StoredNotionSettings("token", "database"),
    )
    window = OxfordToNotionWindow(start_update_check=False)
    combo = window.history_target_combo
    combo.resize(420, combo.sizeHint().height())
    combo.show()
    app.processEvents()

    image = combo.grab().toImage()
    arrow_colors = {
        image.pixelColor(x, y).name()
        for x in range(max(0, image.width() - 34), image.width() - 8)
        for y in range(6, image.height() - 6)
    }

    assert "#64748b" in arrow_colors
    assert "#000000" not in arrow_colors
    window.close()


def test_update_worker_ignores_a_signal_deleted_during_app_close():
    class DeletedSignal:
        def emit(self, _result):
            raise RuntimeError("Signal source has been deleted")

    worker = gui.UpdateWorker(lambda: None)
    worker.signals = SimpleNamespace(completed=DeletedSignal())

    worker.run()

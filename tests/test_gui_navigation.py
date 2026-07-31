import os
from datetime import datetime, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication

import gui
from gui import OxfordToNotionWindow
from history_store import ImportHistoryItem
from settings_store import StoredNotionSettings


def _make_window(monkeypatch, history):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        gui,
        "read_notion_settings",
        lambda: StoredNotionSettings("token", "database"),
    )
    monkeypatch.setattr(gui, "read_app_language", lambda: "en")
    monkeypatch.setattr(gui, "read_history_link_target", lambda: "notion")
    monkeypatch.setattr(gui, "read_performance_diagnostics", lambda: False)
    return app, OxfordToNotionWindow(
        history_reader=lambda: history,
        start_update_check=False,
    )


def _item(word):
    return ImportHistoryItem(
        word,
        f"https://www.notion.so/{word}",
        datetime(2026, 7, 31, tzinfo=timezone.utc).isoformat(),
    )


def test_brand_returns_to_import_from_settings(monkeypatch):
    app, window = _make_window(monkeypatch, [])
    window.show_settings_page()

    window.brand_button.click()

    assert window.stack.currentWidget() is window.main_page
    assert window.nav_import_button.property("active") is True
    window.close()
    assert app is not None


def test_recent_page_lists_all_saved_history_while_import_shows_five(monkeypatch):
    history = [_item(f"word{index}") for index in range(8)]
    app, window = _make_window(monkeypatch, history)

    window.show_recent_page()

    assert window.stack.currentWidget() is window.recent_page
    assert len(window.history_buttons) == 5
    assert len(window.recent_buttons) == 8
    window.close()
    assert app is not None


def test_import_title_wraps_without_clipping_at_minimum_size(monkeypatch):
    app, window = _make_window(monkeypatch, [])
    window.show()
    app.processEvents()
    window.resize(window.minimumSize())
    app.processEvents()

    label = window.main_title_label
    wrapped_height = label.fontMetrics().boundingRect(
        QRect(0, 0, label.width(), 1000),
        Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter,
        label.text(),
    ).height()

    assert label.height() >= wrapped_height
    window.close()


def test_recent_first_item_draws_a_top_border(monkeypatch):
    app, window = _make_window(monkeypatch, [_item("privilege")])
    window.show_recent_page()
    window.show()
    app.processEvents()

    image = window.recent_buttons[0].grab().toImage()
    center_x = image.width() // 2

    assert image.pixelColor(center_x, 0) != image.pixelColor(center_x, 5)
    window.close()

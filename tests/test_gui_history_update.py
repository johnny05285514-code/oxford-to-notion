import os
from datetime import datetime, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import gui
from gui import OxfordToNotionWindow
from history_store import ImportHistoryItem
from import_service import ImportResult
from settings_store import StoredNotionSettings
from update_checker import UpdateInfo


def make_window(monkeypatch, *, history=None, history_adder=None):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        gui,
        "read_notion_settings",
        lambda: StoredNotionSettings("token", "database"),
    )
    monkeypatch.setattr(gui, "read_app_language", lambda: "zh-CN")
    window = OxfordToNotionWindow(
        history_reader=lambda: list(history or []),
        history_adder=history_adder or (lambda _word, _url: list(history or [])),
        start_update_check=False,
    )
    return app, window


def item(word, url=None):
    return ImportHistoryItem(
        word,
        url or f"https://www.notion.so/{word}",
        datetime(2026, 7, 12, tzinfo=timezone.utc).isoformat(),
    )


def test_empty_history_and_no_update_are_hidden(monkeypatch):
    _app, window = make_window(monkeypatch)

    assert window.history_section.isHidden()
    assert window.update_banner.isHidden()

    window.close()


def test_history_buttons_show_five_items_and_open_notion(monkeypatch):
    history = [item(word) for word in ["wonderful", "brutality", "refusal", "one", "two"]]
    _app, window = make_window(monkeypatch, history=history)
    opened = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", lambda url: opened.append(url.toString()))

    assert not window.history_section.isHidden()
    assert [button.text() for button in window.history_buttons] == [
        "wonderful ↗",
        "brutality ↗",
        "refusal ↗",
        "one ↗",
        "two ↗",
    ]

    window.history_buttons[1].click()
    assert opened == ["https://www.notion.so/brutality"]
    window.close()


def test_second_history_row_has_bottom_clearance_at_minimum_window_size(monkeypatch):
    history = [item(word) for word in ["fraternize", "banana", "add", "apple"]]
    app, window = make_window(monkeypatch, history=history)

    window.resize(window.minimumSize())
    window.show()
    app.processEvents()

    last_button = window.history_buttons[-1]
    button_bottom = last_button.mapTo(
        window.history_section,
        last_button.rect().bottomLeft(),
    ).y()

    bottom_clearance = window.history_section.height() - button_bottom - 1

    assert bottom_clearance >= 8
    window.close()


def test_success_controls_fit_without_resizing_or_clipping_history(monkeypatch):
    history = [
        item(word)
        for word in ["predispose", "assassinate", "propagandist", "fraternize", "banana"]
    ]
    app, window = make_window(
        monkeypatch,
        history=history,
        history_adder=lambda _word, _url: history,
    )
    window.resize(window.minimumSize())
    window.show()
    app.processEvents()
    initial_height = window.height()

    window.finish_success(ImportResult("predispose", "https://www.notion.so/predispose"))
    app.processEvents()

    last_button = window.history_buttons[-1]
    button_bottom = last_button.mapTo(
        window.history_section,
        last_button.rect().bottomLeft(),
    ).y()
    bottom_clearance = window.history_section.height() - button_bottom - 1

    assert window.height() == initial_height
    assert window.height() >= window.sizeHint().height()
    assert bottom_clearance >= 8
    window.close()


def test_successful_import_persists_and_refreshes_history(monkeypatch):
    current = []

    def add(word, url):
        current[:] = [item(word, url)]
        return list(current)

    _app, window = make_window(monkeypatch, history=current, history_adder=add)
    window.history_reader = lambda: list(current)

    window.finish_success(
        ImportResult("brutality", "https://www.notion.so/brutality")
    )

    assert not window.history_section.isHidden()
    assert [button.text() for button in window.history_buttons] == ["brutality ↗"]
    window.close()


def test_new_update_banner_is_clickable_and_retranslates(monkeypatch):
    _app, window = make_window(monkeypatch)
    opened = []
    monkeypatch.setattr(gui.QDesktopServices, "openUrl", lambda url: opened.append(url.toString()))
    info = UpdateInfo(
        "1.5.0",
        "https://github.com/johnny05285514-code/oxford-to-notion/releases/tag/v1.5.0",
    )

    window.show_update(info)

    assert not window.update_banner.isHidden()
    assert window.update_label.text() == "发现新版本 v1.5.0"
    assert window.update_button.text() == "查看更新"
    window.update_button.click()
    assert opened == [info.release_url]

    window.set_language("en")
    assert window.update_label.text() == "A new version is available: v1.5.0"
    assert window.update_button.text() == "View update"
    assert window.history_title.text() == "Recently imported"
    window.close()


def test_showing_no_update_hides_existing_banner(monkeypatch):
    _app, window = make_window(monkeypatch)
    window.show_update(UpdateInfo("1.5.0", "https://github.com/example/release"))

    window.show_update(None)

    assert window.update_banner.isHidden()
    window.close()

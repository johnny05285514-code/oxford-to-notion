import os
from datetime import datetime, timezone
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import gui
from gui import OxfordToNotionWindow
from history_store import ImportHistoryItem
from import_service import ImportResult
from settings_store import StoredNotionSettings
from update_checker import UpdateInfo


def make_window(
    monkeypatch,
    *,
    history=None,
    history_adder=None,
    history_link_target="notion",
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        gui,
        "read_notion_settings",
        lambda: StoredNotionSettings("token", "database"),
    )
    monkeypatch.setattr(gui, "read_app_language", lambda: "zh-CN")
    monkeypatch.setattr(gui, "save_app_language", lambda _language: None)
    monkeypatch.setattr(gui, "read_history_link_target", lambda: history_link_target)
    saved_targets = []
    monkeypatch.setattr(gui, "save_history_link_target", saved_targets.append)
    window = OxfordToNotionWindow(
        history_reader=lambda: list(history or []),
        history_adder=history_adder or (lambda *_args: list(history or [])),
        start_update_check=False,
    )
    return app, window, saved_targets


def item(word, url=None, oxford_url=None):
    return ImportHistoryItem(
        word,
        url or f"https://www.notion.so/{word}",
        datetime(2026, 7, 12, tzinfo=timezone.utc).isoformat(),
        oxford_url,
    )


def test_empty_history_and_no_update_are_hidden(monkeypatch):
    _app, window, _saved = make_window(monkeypatch)

    assert window.history_section.isHidden()
    assert window.update_banner.isHidden()

    window.close()


def test_history_buttons_show_five_items_and_open_notion(monkeypatch):
    history = [item(word) for word in ["wonderful", "brutality", "refusal", "one", "two"]]
    _app, window, _saved = make_window(monkeypatch, history=history)
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
    app, window, _saved = make_window(monkeypatch, history=history)

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
    app, window, _saved = make_window(
        monkeypatch,
        history=history,
        history_adder=lambda *_args: history,
    )
    window.resize(window.minimumSize())
    window.show()
    app.processEvents()
    initial_height = window.height()

    window.finish_success(
        ImportResult(
            "predispose",
            "https://www.notion.so/predispose",
            "https://www.oxfordlearnersdictionaries.com/definition/english/predispose",
        )
    )
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

    def add(word, url, oxford_url):
        current[:] = [item(word, url, oxford_url)]
        return list(current)

    _app, window, _saved = make_window(
        monkeypatch,
        history=current,
        history_adder=add,
    )
    window.history_reader = lambda: list(current)

    window.finish_success(
        ImportResult(
            "brutality",
            "https://www.notion.so/brutality",
            "https://www.oxfordlearnersdictionaries.com/definition/english/brutality",
        )
    )

    assert not window.history_section.isHidden()
    assert [button.text() for button in window.history_buttons] == ["brutality ↗"]
    window.close()


def test_new_update_banner_is_clickable_and_retranslates(monkeypatch):
    _app, window, _saved = make_window(monkeypatch)
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
    _app, window, _saved = make_window(monkeypatch)
    window.show_update(UpdateInfo("1.5.0", "https://github.com/example/release"))

    window.show_update(None)

    assert window.update_banner.isHidden()
    window.close()


def test_history_buttons_open_oxford_for_existing_items(monkeypatch):
    history = [item("mother's")]
    _app, window, _saved = make_window(
        monkeypatch,
        history=history,
        history_link_target="oxford",
    )
    opened = []
    monkeypatch.setattr(
        gui.QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()),
    )

    window.history_buttons[0].click()

    assert opened == [
        "https://www.oxfordlearnersdictionaries.com/search/english/direct/?q=mother%27s"
    ]
    window.close()


def test_history_button_opens_saved_oxford_source_url_without_search_redirect(
    monkeypatch,
):
    oxford_url = (
        "https://www.oxfordlearnersdictionaries.com/"
        "definition/english/emit?q=emitted"
    )
    history = [
        SimpleNamespace(
            word="emit",
            page_url="https://www.notion.so/emit",
            imported_at=datetime(2026, 7, 12, tzinfo=timezone.utc).isoformat(),
            oxford_url=oxford_url,
        )
    ]
    _app, window, _saved = make_window(
        monkeypatch,
        history=history,
        history_link_target="oxford",
    )
    opened = []
    monkeypatch.setattr(
        gui.QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()),
    )

    window.history_buttons[0].click()

    assert opened == [oxford_url]
    window.close()


def test_successful_import_passes_oxford_source_url_to_history(monkeypatch):
    added = []

    def add(*values):
        added.append(values)
        return []

    _app, window, _saved = make_window(monkeypatch, history_adder=add)
    result = SimpleNamespace(
        word="emit",
        page_url="https://www.notion.so/emit",
        oxford_url=(
            "https://www.oxfordlearnersdictionaries.com/"
            "definition/english/emit?q=emitted"
        ),
    )

    window.finish_success(result)

    assert added == [(result.word, result.page_url, result.oxford_url)]
    window.close()


def test_enabled_performance_diagnostics_shows_import_timing(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        gui,
        "read_notion_settings",
        lambda: StoredNotionSettings("token", "database"),
    )
    monkeypatch.setattr(gui, "read_app_language", lambda: "en")
    monkeypatch.setattr(gui, "read_performance_diagnostics", lambda: True)
    window = OxfordToNotionWindow(start_update_check=False)

    result = ImportResult(
        "brutality",
        "https://www.notion.so/brutality",
        "https://www.oxfordlearnersdictionaries.com/definition/english/brutality",
        timing=SimpleNamespace(
            oxford_seconds=0.4,
            notion_check_seconds=0.2,
            notion_write_seconds=0.6,
            total_seconds=1.2,
        ),
    )
    window.finish_success(result)

    assert "Oxford 0.4s" in window.status_label.text()
    assert "Total 1.2s" in window.status_label.text()
    window.close()
    assert app is not None


def test_saving_oxford_target_refreshes_all_history_buttons(monkeypatch):
    history = [item("brutality")]
    _app, window, saved = make_window(monkeypatch, history=history)
    opened = []
    monkeypatch.setattr(
        gui.QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()),
    )
    window.show_settings_page()
    oxford_index = window.history_target_combo.findData("oxford")
    window.history_target_combo.setCurrentIndex(oxford_index)

    window.save_settings()
    window.history_buttons[0].click()

    assert saved == ["oxford"]
    assert opened == [
        "https://www.oxfordlearnersdictionaries.com/search/english/direct/?q=brutality"
    ]
    window.close()


def test_success_button_still_opens_notion_when_history_target_is_oxford(monkeypatch):
    _app, window, _saved = make_window(
        monkeypatch,
        history_link_target="oxford",
    )
    opened = []
    monkeypatch.setattr(
        gui.QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()),
    )
    window.finish_success(
        ImportResult(
            "emit",
            "https://www.notion.so/emit",
            "https://www.oxfordlearnersdictionaries.com/definition/english/emit?q=emitted",
        )
    )

    window.open_button.click()

    assert opened == ["https://www.notion.so/emit"]
    window.close()


def test_english_success_history_and_footer_do_not_overlap(monkeypatch):
    history = [
        item(word)
        for word in [
            "predispose",
            "assassinate",
            "propagandist",
            "formidable",
            "attitudinal",
        ]
    ]
    app, window, _saved = make_window(
        monkeypatch,
        history=history,
        history_adder=lambda *_args: history,
    )
    window.set_language("en")
    window.resize(window.minimumSize())
    window.show()
    app.processEvents()

    window.finish_success(
        ImportResult(
            "predispose",
            "https://www.notion.so/predispose",
            "https://www.oxfordlearnersdictionaries.com/definition/english/predispose",
        )
    )
    app.processEvents()

    rendered_text_width = window.status_label.fontMetrics().horizontalAdvance(
        window.status_label.text()
    )
    last_button = window.history_buttons[-1]
    footer_bottom = window.footer_label.mapTo(
        window,
        window.footer_label.rect().bottomLeft(),
    ).y()
    content_bottom = window.centralWidget().mapTo(
        window,
        window.centralWidget().rect().bottomLeft(),
    ).y()

    assert rendered_text_width <= window.status_label.width()
    assert last_button.mapTo(window, last_button.rect().bottomLeft()).y() <= window.height()
    assert footer_bottom <= content_bottom
    window.close()


def test_language_change_does_not_resize_minimum_window(monkeypatch):
    app, window, _saved = make_window(monkeypatch)
    window.show_settings_page()
    window.show()
    app.processEvents()
    window.resize(window.minimumSize())
    app.processEvents()
    size_before = window.size()

    window.set_language("en")
    app.processEvents()

    assert window.size() == size_before
    window.close()

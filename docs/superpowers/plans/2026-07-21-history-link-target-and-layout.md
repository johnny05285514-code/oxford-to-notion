# Recent History Link Target and Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users choose whether recent-history buttons open Notion or Oxford while keeping the English five-item success layout fully visible.

**Architecture:** Persist a validated history-link target beside the existing local application settings, reuse Oxford's official direct-search URL builder for old and new history items, and bind the Settings dropdown to that value. Keep the existing history JSON unchanged; the GUI resolves each destination when it creates the history buttons. Fix the layout at its source by reserving adequate status-text width and scheduling content fitting after every state that can change main-page height.

**Tech Stack:** Python 3.11+, PySide6, python-dotenv, pytest, PyInstaller, NSIS, GitHub Releases

## Global Constraints

- The default recent-history target remains Notion.
- The selected target applies to all existing and future history items.
- The success-state action button always opens the newly created or updated Notion page.
- Do not migrate or rewrite the history JSON format.
- The current minimum window size remains 640 by 600 pixels.
- Missing or invalid target settings fall back to Notion.
- Preserve `.env`, Notion credentials, and import history during upgrade; never include `.env` in build or release artifacts.
- Do not change Oxford parsing, Notion database fields, upsert semantics, or the five-item history limit.

---

### Task 1: Persist the recent-history destination and build safe Oxford links

**Files:**
- Modify: `settings_store.py`
- Modify: `oxford_client.py`
- Modify: `tests/test_settings_store.py`
- Modify: `tests/test_oxford_client.py`

**Interfaces:**
- Produces: `HISTORY_LINK_TARGET_NOTION: str`, `HISTORY_LINK_TARGET_OXFORD: str`
- Produces: `read_history_link_target(*, env_path: Path | None = None) -> str`
- Produces: `save_history_link_target(target: str, *, env_path: Path | None = None) -> None`
- Produces: `build_oxford_search_url(word: str) -> str`
- Consumes: existing `normalize_word(word: str) -> str` validation

- [ ] **Step 1: Write failing persistence tests**

Add these imports and tests to `tests/test_settings_store.py`:

```python
from dotenv import dotenv_values

from settings_store import (
    HISTORY_LINK_TARGET_NOTION,
    HISTORY_LINK_TARGET_OXFORD,
    read_history_link_target,
    save_history_link_target,
)


def test_history_link_target_defaults_to_notion(tmp_path):
    assert read_history_link_target(env_path=tmp_path / ".env") == HISTORY_LINK_TARGET_NOTION


def test_history_link_target_round_trips_and_preserves_credentials(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "NOTION_TOKEN=secret-value\nNOTION_DATABASE_ID=database-value\n",
        encoding="utf-8",
    )

    save_history_link_target(HISTORY_LINK_TARGET_OXFORD, env_path=path)

    assert read_history_link_target(env_path=path) == HISTORY_LINK_TARGET_OXFORD
    values = dotenv_values(path)
    assert values["NOTION_TOKEN"] == "secret-value"
    assert values["NOTION_DATABASE_ID"] == "database-value"


def test_invalid_saved_history_link_target_falls_back_to_notion(tmp_path):
    path = tmp_path / ".env"
    path.write_text("HISTORY_LINK_TARGET=unknown\n", encoding="utf-8")

    assert read_history_link_target(env_path=path) == HISTORY_LINK_TARGET_NOTION


def test_rejects_invalid_history_link_target(tmp_path):
    with pytest.raises(ConfigurationError, match="Unsupported history link target"):
        save_history_link_target("unknown", env_path=tmp_path / ".env")
```

- [ ] **Step 2: Run the persistence tests and verify they fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_settings_store.py -q
```

Expected: collection fails because the new constants and functions do not exist.

- [ ] **Step 3: Add validated persistence**

Add to `settings_store.py`:

```python
HISTORY_LINK_TARGET_NOTION = "notion"
HISTORY_LINK_TARGET_OXFORD = "oxford"
HISTORY_LINK_TARGETS = {
    HISTORY_LINK_TARGET_NOTION,
    HISTORY_LINK_TARGET_OXFORD,
}


def read_history_link_target(*, env_path: Path | None = None) -> str:
    path = env_path or default_env_path()
    values = dotenv_values(path) if path.exists() else {}
    target = (values.get("HISTORY_LINK_TARGET") or "").strip().lower()
    return target if target in HISTORY_LINK_TARGETS else HISTORY_LINK_TARGET_NOTION


def save_history_link_target(
    target: str,
    *,
    env_path: Path | None = None,
) -> None:
    normalized = target.strip().lower()
    if normalized not in HISTORY_LINK_TARGETS:
        raise ConfigurationError(f"Unsupported history link target: {target}")

    path = env_path or default_env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    set_key(str(path), "HISTORY_LINK_TARGET", normalized)
```

- [ ] **Step 4: Add a failing Oxford URL-builder test**

Add to `tests/test_oxford_client.py`:

```python
from oxford_client import build_oxford_search_url


def test_build_oxford_search_url_normalizes_and_encodes_the_word():
    assert build_oxford_search_url("  Mother's  ") == (
        "https://www.oxfordlearnersdictionaries.com/search/english/direct/?q=mother%27s"
    )
```

- [ ] **Step 5: Run the URL-builder test and verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_oxford_client.py::test_build_oxford_search_url_normalizes_and_encodes_the_word -q
```

Expected: collection fails because `build_oxford_search_url` does not exist.

- [ ] **Step 6: Reuse one official Oxford URL builder**

Add to `oxford_client.py` and use it in `OxfordClient.lookup` instead of concatenating `SEARCH_URL` directly:

```python
def build_oxford_search_url(word: str) -> str:
    normalized = normalize_word(word)
    return SEARCH_URL + quote(normalized, safe="")
```

The lookup URL tuple becomes:

```python
urls = (
    BASE_URL + quote(normalized, safe="-'"),
    build_oxford_search_url(normalized),
)
```

- [ ] **Step 7: Run focused tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_settings_store.py tests\test_oxford_client.py -q
```

Expected: all focused tests pass, including the existing `emitted` fallback test.

- [ ] **Step 8: Commit Task 1**

```powershell
git add settings_store.py oxford_client.py tests\test_settings_store.py tests\test_oxford_client.py
git commit -m "Add recent history link preference"
```

---

### Task 2: Add the bilingual Settings control and resolve every history click

**Files:**
- Modify: `gui.py`
- Modify: `i18n.py`
- Modify: `tests/test_gui_history_update.py`
- Modify: `tests/test_gui_language.py`

**Interfaces:**
- Consumes: `read_history_link_target() -> str`
- Consumes: `save_history_link_target(target: str) -> None`
- Consumes: `build_oxford_search_url(word: str) -> str`
- Produces: `OxfordToNotionWindow.history_target_combo: QComboBox`
- Produces: `OxfordToNotionWindow.history_link_target: str`
- Produces: `OxfordToNotionWindow.history_url(item: ImportHistoryItem) -> str`

- [ ] **Step 1: Extend the GUI fixture for target persistence**

Update `make_window` in `tests/test_gui_history_update.py` so tests can choose and capture the stored target:

```python
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
    monkeypatch.setattr(gui, "read_history_link_target", lambda: history_link_target)
    saved_targets = []
    monkeypatch.setattr(gui, "save_history_link_target", saved_targets.append)
    window = OxfordToNotionWindow(
        history_reader=lambda: list(history or []),
        history_adder=history_adder or (lambda _word, _url: list(history or [])),
        start_update_check=False,
    )
    return app, window, saved_targets
```

Adjust existing calls to unpack the third return value.

- [ ] **Step 2: Write failing destination-behaviour tests**

Add to `tests/test_gui_history_update.py`:

```python
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
    window.finish_success(ImportResult("emit", "https://www.notion.so/emit"))

    window.open_button.click()

    assert opened == ["https://www.notion.so/emit"]
    window.close()
```

- [ ] **Step 3: Write failing translation-control tests**

Extend `tests/test_gui_language.py::test_switching_language_retranslates_main_and_settings_pages`:

```python
assert window.history_target_label.text() == "Open recent imports in"
assert [window.history_target_combo.itemText(index) for index in range(2)] == [
    "Notion",
    "Oxford Learner's Dictionaries",
]

window.set_language("zh-CN")
assert window.history_target_label.text() == "最近导入打开方式"
assert [window.history_target_combo.itemText(index) for index in range(2)] == [
    "Notion",
    "Oxford Learner's Dictionaries",
]
```

Add a Settings-page geometry test:

```python
def test_history_target_control_does_not_clip_settings_actions(monkeypatch):
    app, window, _saved = make_window(monkeypatch)
    window.resize(window.minimumSize())
    window.show_settings_page()
    window.show()
    app.processEvents()

    button_bottom = window.settings_save_button.mapTo(
        window,
        window.settings_save_button.rect().bottomLeft(),
    ).y()
    content_bottom = window.centralWidget().mapTo(
        window,
        window.centralWidget().rect().bottomLeft(),
    ).y()

    assert button_bottom <= content_bottom
    window.close()
```

- [ ] **Step 4: Run the new GUI tests and verify they fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_gui_history_update.py tests\test_gui_language.py -q
```

Expected: failures show the dropdown, target reader/saver, and Oxford destination behaviour are not implemented.

- [ ] **Step 5: Add bilingual strings**

Add these keys to both catalogs in `i18n.py`:

```python
# English
"history_target_label": "Open recent imports in",
"history_target_notion": "Notion",
"history_target_oxford": "Oxford Learner's Dictionaries",
"open_history_item_notion": "Open {word} in Notion",
"open_history_item_oxford": "Open {word} in Oxford Learner's Dictionaries",

# Simplified Chinese
"history_target_label": "最近导入打开方式",
"history_target_notion": "Notion",
"history_target_oxford": "Oxford Learner's Dictionaries",
"open_history_item_notion": "在 Notion 中打开 {word}",
"open_history_item_oxford": "在 Oxford Learner's Dictionaries 中打开 {word}",
```

Remove the old single `open_history_item` key after every caller has moved to a destination-specific key.

- [ ] **Step 6: Add and initialize the dropdown**

In `gui.py`, import `QComboBox`, the target constants/read/write functions, and `build_oxford_search_url`. During initialization, load:

```python
self.history_link_target = read_history_link_target()
```

In `_build_settings_page`, place the label and dropdown after the database entry and before the wizard button:

```python
self.history_target_label = QLabel()
layout.addSpacing(18)
layout.addWidget(self.history_target_label)
layout.addSpacing(6)
self.history_target_combo = QComboBox()
self.history_target_combo.addItem("", HISTORY_LINK_TARGET_NOTION)
self.history_target_combo.addItem("", HISTORY_LINK_TARGET_OXFORD)
layout.addWidget(self.history_target_combo)
```

In `retranslate_ui`, update the label, both item texts, and each history tooltip without changing the current item data.

- [ ] **Step 7: Resolve history URLs and save the selection**

Add to `OxfordToNotionWindow`:

```python
def history_url(self, item: ImportHistoryItem) -> str:
    if self.history_link_target == HISTORY_LINK_TARGET_OXFORD:
        return build_oxford_search_url(item.word)
    return item.page_url

def history_tooltip_key(self) -> str:
    if self.history_link_target == HISTORY_LINK_TARGET_OXFORD:
        return "open_history_item_oxford"
    return "open_history_item_notion"
```

When creating each history button, capture `self.history_url(item)` and use `history_tooltip_key()`. In `show_settings_page`, load the current value by item data and schedule content fitting so the added control cannot hide the bottom action row. In `save_settings`, persist the combo's item data, update `self.history_link_target`, refresh history, and then return to the main page:

```python
selected_target = self.history_target_combo.currentData()
save_notion_settings(self.token_entry.text(), self.database_entry.text())
save_history_link_target(selected_target)
self.history_link_target = selected_target
self.refresh_history()
```

- [ ] **Step 8: Run destination and language tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_gui_history_update.py tests\test_gui_language.py tests\test_i18n.py -q
```

Expected: all destination, persistence-through-GUI, tooltip, and bilingual control tests pass.

- [ ] **Step 9: Commit the destination UI**

```powershell
git add gui.py i18n.py tests\test_gui_history_update.py tests\test_gui_language.py
git commit -m "Let recent imports open Oxford"
```

---

### Task 3: Prevent English success/history/footer overlap

**Files:**
- Modify: `gui.py`
- Modify: `tests/test_gui_history_update.py`

**Interfaces:**
- Consumes: existing `schedule_content_fit() -> None`
- Produces: content fitting after every history refresh and language change
- Preserves: 640 by 600 minimum window and five-item three-column grid

- [ ] **Step 1: Write an English five-item regression test**

Add to `tests/test_gui_history_update.py`:

```python
def test_english_success_history_and_footer_do_not_overlap(monkeypatch):
    history = [
        item(word)
        for word in ["predispose", "assassinate", "propagandist", "formidable", "attitudinal"]
    ]
    app, window, _saved = make_window(
        monkeypatch,
        history=history,
        history_adder=lambda _word, _url: history,
    )
    window.set_language("en")
    window.resize(window.minimumSize())
    window.show()
    app.processEvents()

    window.finish_success(ImportResult("predispose", "https://www.notion.so/predispose"))
    app.processEvents()

    line_height = window.status_label.fontMetrics().lineSpacing()
    last_button = window.history_buttons[-1]
    history_bottom = last_button.mapTo(window, last_button.rect().bottomLeft()).y()
    footer_top = window.footer_label.mapTo(window, window.footer_label.rect().topLeft()).y()
    footer_bottom = window.footer_label.mapTo(
        window,
        window.footer_label.rect().bottomLeft(),
    ).y()
    content_bottom = window.centralWidget().mapTo(
        window,
        window.centralWidget().rect().bottomLeft(),
    ).y()

    assert window.status_label.height() <= line_height + 4
    assert footer_top - history_bottom >= 8
    assert footer_bottom <= content_bottom
    window.close()
```

Add a second test proving content fitting is scheduled after language change and history refresh by monkeypatching `window.schedule_content_fit` with a counter and invoking both operations.

- [ ] **Step 2: Run the regression tests and verify the English case fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_gui_history_update.py::test_english_success_history_and_footer_do_not_overlap -q
```

Expected: failure shows the English success label wraps or the footer clearance is below 8 pixels.

- [ ] **Step 3: Give status text stable horizontal room**

In `_build_main_page`, keep word wrapping as a fallback but add:

```python
self.status_label.setMinimumWidth(320)
```

This keeps normal Chinese and English success messages on one line at the minimum window width without disabling wrapping for unusually long words.

- [ ] **Step 4: Fit content after every relevant state change**

At the end of `set_language`, call `schedule_content_fit()`. At the end of `refresh_history`, call it when the main page has been created. Keep the existing calls after success and update-banner changes. Ensure initialization does not access widgets before they exist by guarding with `hasattr(self, "main_page")` where necessary.

- [ ] **Step 5: Run all GUI regression tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_gui.py tests\test_gui_language.py tests\test_gui_history_update.py tests\test_setup_wizard_ui.py -q
```

Expected: all GUI tests pass at the 640 by 600 minimum, with English and Chinese history rows fully above the footer.

- [ ] **Step 6: Commit the layout fix**

```powershell
git add gui.py tests\test_gui_history_update.py
git commit -m "Keep recent history clear in English"
```

---

### Task 4: Document, version, package, install, and publish the patch release

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `update_checker.py`
- Modify: `oxford_client.py`
- Modify: `installer.nsi`
- Modify: `build_installer.bat`
- Modify: `tests/test_update_checker.py`
- Modify: `tests/test_oxford_client.py`
- Modify: `tests/test_installer_files.py`

**Interfaces:**
- Produces: application/release version `1.4.6`
- Produces: `release/Oxford-to-Notion-Setup-1.4.6.exe`
- Produces: matching `.sha256` checksum file
- Preserves: installed `%APPDATA%\Oxford to Notion\.env` and history data

- [ ] **Step 1: Write failing version assertions**

Change existing assertions to require:

```python
assert CURRENT_VERSION == "1.4.6"
assert "Oxford-to-Notion/1.4.6" in session.headers["User-Agent"]
assert 'File /oname=Oxford-to-Notion-v1.4.6.ico "assets\\app-icon.ico"' in script
assert '"$INSTDIR\\Oxford-to-Notion-v1.4.6.ico" 0' in script
```

Also assert the installer deletes the old `Oxford-to-Notion-v1.4.5.ico` during upgrade.

- [ ] **Step 2: Run version tests and verify they fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_update_checker.py tests\test_oxford_client.py tests\test_installer_files.py -q
```

Expected: failures report the existing `1.4.5` values.

- [ ] **Step 3: Update version references and installer cleanup**

Replace application, user-agent, installer, output-file, icon, and README download references from `1.4.5` to `1.4.6`. Add deletion of the v1.4.5 icon to the installer upgrade and uninstall sections. Do not change the GitHub repository URL or install/data directories.

- [ ] **Step 4: Document the feature bilingually**

Add a `v1.4.6 — 2026-07-21` entry to `CHANGELOG.md` describing:

- the Notion/Oxford recent-history destination preference;
- immediate application to old and new history entries;
- the unchanged success button destination; and
- the English success/history/footer clipping fix.

Update the recent-history paragraphs in both READMEs and mention the new dropdown under Settings. Keep the personal low-frequency-use statement unchanged.

- [ ] **Step 5: Run the complete test suite**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Expected: every test passes with no warnings caused by this change.

- [ ] **Step 6: Run focused live and safety checks**

Run a read-only Oxford lookup for `emitted` and verify the canonical word is still `emit`. Search tracked files and build inputs for Notion token patterns and verify `.env` is untracked and excluded. Confirm `git diff --check` is clean.

- [ ] **Step 7: Commit release metadata and documentation**

```powershell
git add CHANGELOG.md README.md README.en.md update_checker.py oxford_client.py installer.nsi build_installer.bat tests\test_update_checker.py tests\test_oxford_client.py tests\test_installer_files.py
git commit -m "Prepare v1.4.6 release"
```

- [ ] **Step 8: Build and verify the installer**

Run:

```powershell
build_installer.bat --no-pause
Get-FileHash release\Oxford-to-Notion-Setup-1.4.6.exe -Algorithm SHA256
Get-Content release\Oxford-to-Notion-Setup-1.4.6.exe.sha256
```

Expected: the installer and checksum file exist and both SHA-256 values match.

- [ ] **Step 9: Upgrade the local installed copy**

Close the running app, run the v1.4.6 installer, and verify Windows reports version 1.4.6. Confirm the Start-menu/desktop shortcut uses the current icon and that only the current application version remains installed. Reopen the app and verify the existing Notion configuration and recent history remain available.

- [ ] **Step 10: Publish and verify GitHub v1.4.6**

Merge the completed branch into `main`, push `main`, create tag `v1.4.6`, and publish a GitHub Release containing only:

```text
Oxford-to-Notion-Setup-1.4.6.exe
Oxford-to-Notion-Setup-1.4.6.exe.sha256
```

Verify the public release page, asset names, downloadable checksum, README version, and absence of `.env` or credentials.

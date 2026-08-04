# Recent History Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add instant, case-insensitive substring search to the Recent history page.

**Architecture:** `OxfordToNotionWindow` retains the currently loaded history list, renders the Import-page summary from the full list, and renders the Recent-page list from a filtered view. A `QLineEdit` on the Recent page triggers filtering on each text change. Existing history buttons continue to decide their URLs through `history_url`.

**Tech Stack:** Python 3.11+, PySide6, pytest.

## Global Constraints

- Search only the local Recent page; do not modify `history.json`, Notion data, Oxford queries, or the five-item Import summary.
- Match case-insensitively against any part of the word; trim surrounding query whitespace.
- Preserve the existing Notion/Oxford click preference and bilingual UI.

---

### Task 1: Add searchable Recent-list rendering

**Files:**
- Modify: `gui.py:574-596, 716-750, 916-939`
- Modify: `i18n.py:20-40, 115-135`
- Test: `tests/test_gui_history_update.py`

**Interfaces:**
- Consumes: `ImportHistoryItem.word`, `OxfordToNotionWindow._history_button(item, "recentItem")`, and `Translator.text(key)`.
- Produces: `OxfordToNotionWindow.recent_search_entry: QLineEdit`, `OxfordToNotionWindow.filter_recent_history(query: str) -> None`, and an updated `recent_buttons` list containing only visible matches.

- [ ] **Step 1: Write failing tests for filtering and empty results**

```python
def test_recent_search_matches_substrings_case_insensitively(monkeypatch):
    history = [item(word) for word in ["wonderful", "emitted", "emitter"]]
    _app, window, _saved = make_window(monkeypatch, history=history)

    window.show_recent_page()
    window.recent_search_entry.setText("MIT")

    assert [button.property("word") for button in window.recent_buttons] == [
        "emitted", "emitter"
    ]
    assert window.recent_empty_label.isHidden()
    window.close()


def test_recent_search_shows_no_match_message_and_clears_back_to_all_items(monkeypatch):
    history = [item(word) for word in ["brutality", "wonderful"]]
    _app, window, _saved = make_window(monkeypatch, history=history)

    window.show_recent_page()
    window.recent_search_entry.setText("zzz")

    assert window.recent_buttons == []
    assert window.recent_empty_label.text() == "No matching imported words."

    window.recent_search_entry.setText("   ")

    assert [button.property("word") for button in window.recent_buttons] == [
        "brutality", "wonderful"
    ]
    window.close()
```

- [ ] **Step 2: Run the two tests to verify they fail**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider --basetemp='work\pytest-temp' tests/test_gui_history_update.py -k recent_search
```

Expected: FAIL because `recent_search_entry` and filtered rendering do not exist.

- [ ] **Step 3: Add localized search and empty-result messages**

```python
ENGLISH_MESSAGES.update(
    {
        "recent_search_placeholder": "Search imported words",
        "recent_no_match": "No matching imported words.",
    }
)

CHINESE_MESSAGES.update(
    {
        "recent_search_placeholder": "搜索已导入的单词",
        "recent_no_match": "没有匹配的导入单词。",
    }
)
```

- [ ] **Step 4: Add the search input and minimal filtered rendering**

```python
self.recent_search_entry = QLineEdit()
self.recent_search_entry.textChanged.connect(self.filter_recent_history)
layout.addWidget(self.recent_search_entry)

def filter_recent_history(self, query: str) -> None:
    normalized = query.strip().casefold()
    matches = [
        item for item in self.current_history
        if not normalized or normalized in item.word.casefold()
    ]
    self._render_recent_history(matches, has_history=bool(self.current_history))
```

`refresh_history` must set `self.current_history`, update the five-item Import grid from that full list, and then call `filter_recent_history(self.recent_search_entry.text())`. `_render_recent_history` must rebuild only `recent_layout`, populate `recent_buttons`, and show `recent_empty` for no history or `recent_no_match` for a non-empty filtered-out list. `retranslate_ui` must update the search placeholder and re-run the current query so a visible no-match message changes language immediately.

- [ ] **Step 5: Run the focused tests to verify they pass**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider --basetemp='work\pytest-temp' tests/test_gui_history_update.py -k recent_search
```

Expected: PASS.

- [ ] **Step 6: Run related navigation and language regression tests**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider --basetemp='work\pytest-temp' tests/test_gui_history_update.py tests/test_gui_language.py tests/test_gui_navigation.py
```

Expected: PASS.

- [ ] **Step 7: Commit the feature**

```powershell
git add -- gui.py i18n.py tests/test_gui_history_update.py
git commit -m "Add recent history search"
```

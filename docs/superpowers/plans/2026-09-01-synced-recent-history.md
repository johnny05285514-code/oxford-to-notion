# Synced Recent History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Notion the authoritative source for the 100 most recent imports while preserving an immediate, searchable local cache when sync is unavailable.

**Architecture:** `NotionWriter` will expose a read-only `list_recent()` boundary that returns validated `ImportHistoryItem` values. A small `recent_sync.py` service will build the Notion dependency and atomically replace `history.json`; a dedicated Qt worker will call that service without blocking imports or navigation.

**Tech Stack:** Python 3.11+, notion-client 2.7.0, PySide6 Essentials, JSON cache, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-macos-arm64-and-synced-recent-design.md`

## Global Constraints

- Query at most 100 Notion pages, sorted by `Added Date` descending.
- Never write to Notion during a Recent refresh.
- Preserve cached records on every sync failure.
- Keep Recent substring search case-insensitive and unchanged.
- Keep the Import-page summary limited to five items.
- Never persist a Notion token, definition text, examples, or Oxford HTML in `history.json`.
- Run sync work outside the GUI thread and allow only one sync request at a time.
- Refresh on configured startup, after a successful import, and on Recent navigation when the prior attempt is at least 60 seconds old.
- Preserve user-authored Notion blocks on repeat import.
- Add all visible copy in English and Simplified Chinese.

---

### Task 1: Atomic authoritative cache replacement

**Files:**
- Modify: `history_store.py`
- Test: `tests/test_history_store.py`

**Interfaces:**
- Consumes: existing `ImportHistoryItem` and `MAX_HISTORY_ITEMS`.
- Produces: `replace_history_items(items: list[ImportHistoryItem], *, path: Path | None = None) -> list[ImportHistoryItem]`.

- [ ] **Step 1: Write failing replacement tests**

Add these imports and tests to `tests/test_history_store.py`:

```python
import json

from history_store import ImportHistoryItem, add_history_item, read_history, replace_history_items


def test_replace_history_items_atomically_replaces_cache(tmp_path):
    path = tmp_path / "nested" / "history.json"
    old = ImportHistoryItem("old", "https://notion.so/old", "2026-08-01")
    new = ImportHistoryItem(
        "emitted",
        "https://notion.so/emitted",
        "2026-09-01",
        "https://www.oxfordlearnersdictionaries.com/definition/english/emit",
    )
    replace_history_items([old], path=path)

    result = replace_history_items([new], path=path)

    assert result == [new]
    assert read_history(path) == [new]
    assert not path.with_suffix(".tmp").exists()


def test_replace_history_items_discards_invalid_and_limits_to_one_hundred(tmp_path):
    path = tmp_path / "history.json"
    valid = [
        ImportHistoryItem(f"word-{index}", f"https://notion.so/{index}", "2026-09-01")
        for index in range(105)
    ]
    unsafe = ImportHistoryItem("unsafe", "javascript:alert(1)", "2026-09-01")

    result = replace_history_items([unsafe, *valid], path=path)

    assert len(result) == 100
    assert result[0].word == "word-0"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload["items"]) == 100
```

- [ ] **Step 2: Run the tests and verify the missing interface fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_history_store.py -q
```

Expected: collection fails because `replace_history_items` is not defined.

- [ ] **Step 3: Extract the atomic writer and implement replacement**

Add this minimal structure to `history_store.py`, then route `add_history_item()` through `_write_history_items()`:

```python
def _validated_items(items: list[ImportHistoryItem]) -> list[ImportHistoryItem]:
    validated = [
        parsed
        for item in items
        if (parsed := _parse_item(asdict(item))) is not None
    ]
    return validated[:MAX_HISTORY_ITEMS]


def _write_history_items(
    items: list[ImportHistoryItem],
    target: Path,
) -> list[ImportHistoryItem]:
    validated = _validated_items(items)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    payload = {"items": [asdict(item) for item in validated]}
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return read_history(target)
    return validated


def replace_history_items(
    items: list[ImportHistoryItem],
    *,
    path: Path | None = None,
) -> list[ImportHistoryItem]:
    return _write_history_items(items, path or default_history_path())
```

In `add_history_item()`, replace the duplicated directory/temp-file block with:

```python
return _write_history_items(items, target)
```

- [ ] **Step 4: Run focused and existing cache tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_history_store.py -q
```

Expected: all history-store tests pass, including write-failure behavior.

- [ ] **Step 5: Commit the cache boundary**

```powershell
git add history_store.py tests/test_history_store.py
git commit -m "Add authoritative recent history cache replacement"
```

---

### Task 2: Read Recent records from Notion and refresh duplicate dates

**Files:**
- Modify: `exceptions.py`
- Modify: `notion_writer.py`
- Modify: `tests/test_notion_writer.py`

**Interfaces:**
- Consumes: `ImportHistoryItem` from `history_store.py`.
- Produces: `NotionWriter.list_recent(limit: int = 100) -> list[ImportHistoryItem]`.
- Produces: `NotionSyncError(NotionError)` for categorized read failures.

- [ ] **Step 1: Write failing Notion Recent tests**

Extend `tests/test_notion_writer.py` with a page factory and these cases:

```python
from exceptions import NotionSchemaError, NotionSyncError, NotionWriteError


def recent_page(word="emitted", added="2026-09-01", source_url="https://oxford.test/emit"):
    return {
        "id": f"page-{word}",
        "url": f"https://notion.so/{word}",
        "properties": {
            "Word": {"type": "rich_text", "rich_text": [{"plain_text": word}]},
            "Source URL": {"type": "url", "url": source_url},
            "Added Date": {"type": "date", "date": {"start": added}},
        },
    }


def test_list_recent_queries_one_sorted_page_and_normalizes_records():
    client = FakeClient([recent_page()])
    writer = NotionWriter(client, "database-id")

    items = writer.list_recent()

    assert [item.word for item in items] == ["emitted"]
    assert items[0].page_url == "https://notion.so/emitted"
    assert items[0].oxford_url == "https://oxford.test/emit"
    name, kwargs = client.data_sources.calls[-1]
    assert name == "query"
    assert kwargs["page_size"] == 100
    assert kwargs["sorts"] == [{"property": "Added Date", "direction": "descending"}]


def test_list_recent_skips_malformed_individual_pages():
    malformed = recent_page(word="")
    malformed["url"] = "javascript:alert(1)"
    client = FakeClient([malformed, recent_page(word="valid")])

    assert [item.word for item in NotionWriter(client, "database-id").list_recent()] == ["valid"]


def test_list_recent_wraps_notion_transport_failures():
    client = FakeClient([])
    client.data_sources = Endpoint(
        retrieve={"properties": REQUIRED_SCHEMA},
        query=RequestTimeoutError(),
    )

    with pytest.raises(NotionSyncError, match="Notion recent history request failed"):
        NotionWriter(client, "database-id").list_recent()
```

Update the repeat-import assertion:

```python
writer = NotionWriter(client, "database-id", today=lambda: date(2026, 9, 1))
url = writer.upsert(ENTRY)
update = next(kwargs for name, kwargs in client.pages.calls if name == "update")
assert update["properties"]["Added Date"]["date"]["start"] == "2026-09-01"
```

- [ ] **Step 2: Run focused tests and verify failures**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_notion_writer.py -q
```

Expected: failures for missing `NotionSyncError`, missing `list_recent()`, and the unchanged duplicate date.

- [ ] **Step 3: Add the sync exception and page parser**

Add to `exceptions.py`:

```python
class NotionSyncError(NotionError):
    pass
```

Import `ImportHistoryItem` and `NotionSyncError` in `notion_writer.py`, then add focused helpers:

```python
@staticmethod
def _plain_text_property(properties: dict[str, Any], name: str) -> str:
    prop = properties.get(name, {})
    parts = prop.get(prop.get("type", ""), [])
    return "".join(
        part.get("plain_text") or part.get("text", {}).get("content", "")
        for part in parts
    ).strip()


@classmethod
def _recent_item(cls, page: dict[str, Any]) -> ImportHistoryItem | None:
    properties = page.get("properties", {})
    word = cls._plain_text_property(properties, "Word")
    page_url = page.get("url", "")
    source_url = properties.get("Source URL", {}).get("url")
    added = properties.get("Added Date", {}).get("date") or {}
    added_at = added.get("start", "")
    candidate = ImportHistoryItem(word, page_url, added_at, source_url)
    return candidate if word and page_url and added_at else None
```

Use the existing cache validation when records are written; `list_recent()` itself must also reject malformed URLs by checking that both page and Oxford URLs use HTTP(S), or by exposing a small public normalization helper from `history_store.py` if tests show duplication.

- [ ] **Step 4: Implement the read-only query and duplicate date refresh**

Add to `NotionWriter`:

```python
def list_recent(self, limit: int = 100) -> list[ImportHistoryItem]:
    bounded_limit = max(1, min(limit, 100))
    try:
        data_source_id, schema = self._resolve_data_source()
        self._validate_schema(schema)
        response = self.client.data_sources.query(
            data_source_id=data_source_id,
            sorts=[{"property": "Added Date", "direction": "descending"}],
            page_size=bounded_limit,
        )
        items = [
            item
            for page in response.get("results", [])
            if (item := self._recent_item(page)) is not None
        ]
        return items[:bounded_limit]
    except NotionSchemaError:
        raise
    except (
        APIResponseError,
        HTTPResponseError,
        RequestTimeoutError,
        httpx.RequestError,
        OSError,
    ) as exc:
        raise NotionSyncError("Notion recent history request failed.") from exc
```

In the existing-page branch of `upsert()`, change:

```python
properties=build_properties(entry),
```

to:

```python
properties=build_properties(entry, self.today()),
```

- [ ] **Step 5: Run Notion tests**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_notion_writer.py tests/test_localized_errors.py -q
```

Expected: all tests pass; repeat imports preserve blocks and now refresh `Added Date`.

- [ ] **Step 6: Commit the Notion read boundary**

```powershell
git add exceptions.py notion_writer.py tests/test_notion_writer.py
git commit -m "Read recent imports from Notion"
```

---

### Task 3: Create the Recent synchronization service

**Files:**
- Create: `recent_sync.py`
- Create: `tests/test_recent_sync.py`

**Interfaces:**
- Consumes: `Settings.from_env()`, `NotionWriter.list_recent()`, and `replace_history_items()`.
- Produces: `build_recent_reader() -> NotionWriter`.
- Produces: `sync_recent_history(*, reader: Any | None = None, cache_writer: Callable = replace_history_items) -> list[ImportHistoryItem]`.

- [ ] **Step 1: Write failing service tests**

Create `tests/test_recent_sync.py`:

```python
from history_store import ImportHistoryItem
from recent_sync import sync_recent_history


class FakeReader:
    def __init__(self, items):
        self.items = items
        self.limits = []

    def list_recent(self, limit=100):
        self.limits.append(limit)
        return self.items


def test_sync_recent_history_queries_one_hundred_and_replaces_cache():
    items = [ImportHistoryItem("emit", "https://notion.so/emit", "2026-09-01")]
    reader = FakeReader(items)
    written = []

    result = sync_recent_history(
        reader=reader,
        cache_writer=lambda records: written.extend(records) or list(records),
    )

    assert reader.limits == [100]
    assert written == items
    assert result == items


def test_sync_recent_history_does_not_replace_cache_when_query_fails():
    class BrokenReader:
        def list_recent(self, limit=100):
            raise RuntimeError("offline")

    writes = []
    try:
        sync_recent_history(reader=BrokenReader(), cache_writer=lambda records: writes.append(records))
    except RuntimeError as error:
        assert str(error) == "offline"
    else:
        raise AssertionError("sync should preserve and re-raise the query failure")
    assert writes == []
```

- [ ] **Step 2: Run the new tests and verify import failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_recent_sync.py -q
```

Expected: collection fails because `recent_sync.py` does not exist.

- [ ] **Step 3: Implement the focused service**

Create `recent_sync.py`:

```python
from collections.abc import Callable
from typing import Any

from notion_client import Client

from config import Settings
from history_store import ImportHistoryItem, replace_history_items
from notion_writer import NotionWriter


def build_recent_reader() -> NotionWriter:
    settings = Settings.from_env()
    client = Client(auth=settings.notion_token)
    return NotionWriter(client, settings.notion_database_id)


def sync_recent_history(
    *,
    reader: Any | None = None,
    cache_writer: Callable[[list[ImportHistoryItem]], list[ImportHistoryItem]] = replace_history_items,
) -> list[ImportHistoryItem]:
    active_reader = reader or build_recent_reader()
    items = active_reader.list_recent(limit=100)
    return cache_writer(items)
```

- [ ] **Step 4: Run service and dependency tests**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_recent_sync.py tests/test_config.py tests/test_history_store.py -q
```

Expected: all pass and a failed read never calls the cache writer.

- [ ] **Step 5: Commit the service**

```powershell
git add recent_sync.py tests/test_recent_sync.py
git commit -m "Add recent history synchronization service"
```

---

### Task 4: Integrate non-blocking synchronization into the GUI

**Files:**
- Modify: `gui.py`
- Modify: `i18n.py`
- Modify: `tests/test_gui_history_update.py`
- Modify: `tests/test_gui.py`
- Modify: `tests/test_i18n.py`

**Interfaces:**
- Consumes: `sync_recent_history() -> list[ImportHistoryItem]`.
- Produces: `RecentSyncWorker(sync_func: Callable[[], list[ImportHistoryItem]])` with `succeeded(object)` and `failed(str)` signals.
- Produces: `OxfordToNotionWindow.start_recent_sync(force: bool = False) -> None`.
- Produces: `OxfordToNotionWindow.finish_recent_sync(items: list[ImportHistoryItem]) -> None` and `fail_recent_sync(message: str) -> None`.

- [ ] **Step 1: Extend the GUI test helper without enabling live network work**

Change `make_window()` in `tests/test_gui_history_update.py` to accept `recent_sync_func` and `enable_recent_sync`, passing both into the window. Keep `enable_recent_sync=False` by default:

```python
def make_window(
    monkeypatch,
    *,
    history=None,
    history_adder=None,
    history_link_target="notion",
    recent_sync_func=lambda: [],
    enable_recent_sync=False,
):
    # existing monkeypatch setup remains unchanged
    window = OxfordToNotionWindow(
        history_reader=lambda: list(history or []),
        history_adder=history_adder or (lambda *_args: list(history or [])),
        recent_sync_func=recent_sync_func,
        enable_recent_sync=enable_recent_sync,
        start_update_check=False,
    )
    return app, window, saved_targets
```

- [ ] **Step 2: Write failing worker and window-state tests**

Add tests that use the existing holding-pool pattern:

```python
def test_recent_sync_success_replaces_visible_history(monkeypatch):
    cached = [item("cached")]
    synced = [item("windows-word"), item("mac-word")]
    _app, window, _saved = make_window(
        monkeypatch,
        history=cached,
        recent_sync_func=lambda: synced,
        enable_recent_sync=True,
    )
    worker = window.recent_sync_thread_pool.jobs[-1]

    worker.run()

    assert [entry.word for entry in window.current_history] == ["windows-word", "mac-word"]
    assert window.recent_sync_notice.isHidden()
    window.close()


def test_recent_sync_failure_keeps_cache_and_shows_notice(monkeypatch):
    cached = [item("cached")]

    def fail():
        raise RuntimeError("offline")

    _app, window, _saved = make_window(
        monkeypatch,
        history=cached,
        recent_sync_func=fail,
        enable_recent_sync=True,
    )
    window.recent_sync_thread_pool.jobs[-1].run()

    assert [entry.word for entry in window.current_history] == ["cached"]
    assert "本机记录" in window.recent_sync_notice.text()
    window.close()


def test_recent_sync_suppresses_duplicates_and_honors_sixty_seconds(monkeypatch):
    ticks = iter([0.0, 30.0, 61.0])
    _app, window, _saved = make_window(monkeypatch, enable_recent_sync=False)
    window.recent_sync_clock = lambda: next(ticks)
    window.recent_sync_thread_pool = HoldingThreadPool()
    window.enable_recent_sync = True

    window.start_recent_sync()
    window.start_recent_sync()
    window._recent_sync_running = False
    window.start_recent_sync()

    assert len(window.recent_sync_thread_pool.jobs) == 2
    window.close()
```

Add a success-import test that asserts the local item appears immediately and a forced sync job is queued. Add a language test that changes the active language after a failed sync and verifies the notice changes to English.

- [ ] **Step 3: Run focused GUI tests and verify missing interfaces**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest tests/test_gui_history_update.py tests/test_gui.py tests/test_i18n.py -q
```

Expected: failures for missing constructor parameters, worker, pool, notice, and translations.

- [ ] **Step 4: Add Recent worker types and constructor state**

In `gui.py`, import `monotonic` and `sync_recent_history`, then add:

```python
RECENT_SYNC_INTERVAL_SECONDS = 60.0


class RecentSyncSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)


class RecentSyncWorker(QRunnable):
    def __init__(self, sync_func: Callable[[], list[ImportHistoryItem]]) -> None:
        super().__init__()
        self.sync_func = sync_func
        self.signals = RecentSyncSignals()

    @Slot()
    def run(self) -> None:
        try:
            items = self.sync_func()
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        else:
            self.signals.succeeded.emit(items)
```

Extend the window constructor with:

```python
recent_sync_func: Callable[[], list[ImportHistoryItem]] = sync_recent_history,
enable_recent_sync: bool = False,
recent_sync_clock: Callable[[], float] = monotonic,
```

Initialize a dedicated one-thread `recent_sync_thread_pool`, `_recent_sync_running = False`, and `_last_recent_sync_attempt: float | None = None`. Do not reuse the import worker pool.

- [ ] **Step 5: Add the notice and synchronization state machine**

Place `recent_sync_notice = QLabel(objectName="muted")` below the Recent subtitle, enable word wrapping, and hide it initially. Implement:

```python
def start_recent_sync(self, *, force: bool = False) -> None:
    if not self.enable_recent_sync or self._recent_sync_running:
        return
    now = self.recent_sync_clock()
    if (
        not force
        and self._last_recent_sync_attempt is not None
        and now - self._last_recent_sync_attempt < RECENT_SYNC_INTERVAL_SECONDS
    ):
        return
    self._last_recent_sync_attempt = now
    self._recent_sync_running = True
    worker = RecentSyncWorker(self.recent_sync_func)
    worker.signals.succeeded.connect(self.finish_recent_sync)
    worker.signals.failed.connect(self.fail_recent_sync)
    self.recent_sync_thread_pool.start(worker)


@Slot(object)
def finish_recent_sync(self, items: list[ImportHistoryItem]) -> None:
    self._recent_sync_running = False
    self.recent_sync_notice.hide()
    self.refresh_history(items)


@Slot(str)
def fail_recent_sync(self, _message: str) -> None:
    self._recent_sync_running = False
    self.recent_sync_notice.setText(self.translator.text("recent_sync_cached"))
    self.recent_sync_notice.show()
```

Call `start_recent_sync()` after initial cached rendering when stored settings are complete, from `show_recent_page()`, and after setup completes. In `finish_success()`, keep the immediate `history_adder()` call, then call `start_recent_sync(force=True)`.

- [ ] **Step 6: Add bilingual copy and retranslation**

Use these exact messages in `i18n.py`:

```python
# English
"recent_subtitle": "Your 100 most recent imports are synced through Notion and cached on this device.",
"recent_sync_cached": "Sync is temporarily unavailable. Showing cached history.",

# Simplified Chinese
"recent_subtitle": "最近导入的 100 个单词会通过 Notion 同步，并缓存在这台设备上。",
"recent_sync_cached": "暂时无法同步，正在显示本机记录。",
```

When `retranslate_ui()` runs, update the notice text if it is visible.

- [ ] **Step 7: Run focused GUI tests**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest tests/test_gui_history_update.py tests/test_gui_navigation.py tests/test_gui.py tests/test_i18n.py -q
```

Expected: all pass; imports and Recent navigation remain responsive in offscreen Qt.

- [ ] **Step 8: Commit GUI synchronization**

```powershell
git add gui.py i18n.py tests/test_gui_history_update.py tests/test_gui.py tests/test_i18n.py
git commit -m "Sync recent imports in the background"
```

---

### Task 5: Complete regression verification

**Files:**
- Modify only if a test exposes a regression in files changed by Tasks 1-4.
- Test: complete `tests/` suite.

**Interfaces:**
- Consumes: all synced Recent interfaces from Tasks 1-4.
- Produces: a clean, fully tested checkpoint ready for macOS packaging.

- [ ] **Step 1: Run the full suite in a project-owned temp directory**

```powershell
if (Test-Path work\pytest-synced-recent) { Remove-Item -LiteralPath work\pytest-synced-recent -Recurse -Force }
.\.venv\Scripts\python.exe -m pytest -q --basetemp work\pytest-synced-recent
```

Expected: all tests pass with no network access.

- [ ] **Step 2: Build and smoke-launch the Windows application**

```powershell
cmd /c "build_app.bat --no-pause"
```

Expected: PyInstaller succeeds and `dist\Oxford to Notion.exe` is created. Launch it, confirm the responsive `Oxford to Notion` window appears, and close it without importing.

- [ ] **Step 3: Verify private Windows files were not changed by build or tests**

Compare SHA-256 hashes before and after for existing files under `%APPDATA%\Oxford to Notion`, especially `.env`, `history.json`, and `update-state.json`. Expected: all pre-existing hashes match.

- [ ] **Step 4: Review the diff for scope**

```powershell
git status --short
git diff --stat HEAD~4..HEAD
git diff --check HEAD~4..HEAD
```

Expected: only Recent cache, Notion read/update, GUI synchronization, translations, and their tests changed.

- [ ] **Step 5: Handle any regression without a catch-all commit**

If Step 1 or Step 2 fails, return to the task that owns the failing behavior, add the smallest failing test there, correct only that task's listed source file, and repeat that task's exact staging and commit command. If no correction is needed, do not create an empty commit.

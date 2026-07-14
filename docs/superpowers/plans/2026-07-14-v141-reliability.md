# v1.4.1 Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release v1.4.1 with non-destructive Notion updates, trustworthy connection tests, complete network error handling, and reproducible Notion SDK compatibility.

**Architecture:** Treat one marker toggle as the app-owned page-body boundary. Replace it using create-before-delete semantics, while legacy unmarked blocks remain untouched. Bind asynchronous connection results to the submitted credential pair and normalize transport failures at the Notion boundary.

**Tech Stack:** Python 3.11+, notion-client 2.7.0, httpx, PySide6, pytest, PyInstaller, NSIS.

## Global Constraints

- Never expose or commit `.env`, Notion Token, database ID, private page URL, or full Oxford HTML.
- Do not delete any unmarked Notion page-body block.
- Preserve `Added Date` on updates and continue deduplicating by `Word`.
- Keep Chinese and English user-facing errors aligned.

---

### Task 1: Non-destructive Notion page updates

**Files:**
- Modify: `tests/test_notion_writer.py`
- Modify: `notion_writer.py`

**Interfaces:**
- Produces: `build_managed_container()`, managed-block detection, safe replacement helpers.
- Preserves: `NotionWriter.upsert(entry) -> str`.

- [ ] Add tests proving legacy blocks remain, old managed blocks are deleted only after the new container is populated, and an append failure leaves old content intact.
- [ ] Run the focused tests and confirm they fail because the current implementation deletes every child.
- [ ] Add the marker toggle and create-before-delete replacement algorithm.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Connection-test race protection

**Files:**
- Modify: `tests/test_setup_wizard_ui.py`
- Modify: `tests/test_gui.py`
- Modify: `setup_wizard.py`
- Modify: `gui.py`

**Interfaces:**
- Stores: exact `(token, database)` submitted by each active connection test.
- Accepts success only when current inputs still match the stored pair.

- [ ] Add tests that start a connection test, edit the fields, then deliver the old success callback.
- [ ] Confirm the tests fail because the stale callback currently enables completion or shows success.
- [ ] Compare callback state with the submitted values and keep completion disabled when stale.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Notion transport error normalization

**Files:**
- Modify: `tests/test_notion_writer.py`
- Modify: `tests/test_notion_connection.py`
- Modify: `notion_writer.py`
- Modify: `notion_connection.py`
- Modify: `requirements.txt`

**Interfaces:**
- Converts: `httpx.RequestError` and `HTTPResponseError` to `NotionWriteError` or `NotionConnectionError`.

- [ ] Add failing tests using `httpx.ConnectError` and Notion `HTTPResponseError` substitutes.
- [ ] Add explicit error handling without leaking endpoint or Token details.
- [ ] Fix `notion-client==2.7.0` and declare compatible `httpx` directly.
- [ ] Run focused and dependency checks.

### Task 4: Version, documentation, and release verification

**Files:**
- Create: `CHANGELOG.md`
- Modify: `update_checker.py`
- Modify: `oxford_client.py`
- Modify: `installer.nsi`
- Modify: `build_installer.bat`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: affected version tests

**Interfaces:**
- Publishes: v1.4.1 installer and SHA-256 checksum.

- [ ] Bump every application and installer version reference to `1.4.1`.
- [ ] Add bilingual changelog entries, including the one-time safe migration behavior for legacy pages.
- [ ] Run the full test suite and a read-only live `brutality` lookup.
- [ ] Scan tracked/public files for secrets.
- [ ] Build the executable and installer; verify version metadata and SHA-256.
- [ ] Install locally only after verification, confirm saved configuration remains, then commit, push, and publish the GitHub release.

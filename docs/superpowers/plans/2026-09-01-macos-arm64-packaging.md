# macOS ARM64 Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for every change and superpowers:verification-before-completion before reporting success.

**Goal:** Produce a private, unsigned Apple-silicon `.dmg` for M3 testing while keeping one PySide6 codebase for Windows and macOS.

**Architecture:** Keep `gui.py` as the shared entry point. Add platform-aware user-data paths, a non-interactive packaged-app smoke mode, small macOS build scripts, and a manually triggered GitHub Actions job on an ARM64 macOS runner. The first artifact is for M3 acceptance testing; public Release publication is outside this plan.

**Tech Stack:** Python 3.11+, PySide6 Essentials, PyInstaller 6, pytest, Bash, `sips`, `iconutil`, `codesign`, `hdiutil`, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-01-macos-arm64-and-synced-recent-design.md`

## Global Constraints

- Complete `2026-09-01-synced-recent-history.md` first.
- Target Apple silicon (`arm64`) only.
- Never bundle `.env`, Notion tokens, local history, or other user data.
- Do not add paid signing, notarization, Intel packaging, automatic installation, or a public Release.
- Preserve the existing Windows build and installer.
- Smoke-test the packaged executable before uploading it.

---

### Task 1: Use the correct macOS data directory

**Files:** Modify `app_paths.py`; create `tests/test_app_paths.py`.

- [ ] **Write failing tests** for these exact outcomes:
  - frozen macOS: `~/Library/Application Support/Oxford to Notion`;
  - frozen Windows: `%APPDATA%/Oxford to Notion`;
  - source execution: the repository directory.

The macOS test must patch `app_paths.sys.frozen`, `app_paths.sys.platform`, and `Path.home`; the Windows test must patch `APPDATA`. It must not depend on the host OS.

- [ ] **Prove the new macOS test fails**:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_app_paths.py -q
```

- [ ] **Implement the smallest platform branch** in `app_directory()`:

```python
if getattr(sys, "frozen", False):
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Oxford to Notion"
    app_data = os.getenv("APPDATA")
    base = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
    return base / "Oxford to Notion"
```

- [ ] **Verify and commit**:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_app_paths.py -q
git add app_paths.py tests/test_app_paths.py
git commit -m "Support macOS application data paths"
```

---

### Task 2: Add a packaged-app smoke mode

**Files:** Modify `gui.py`, `build_app.bat`, `tests/test_build_scripts.py`; create `tests/test_gui_smoke.py`.

- [ ] **Write a failing GUI entry-point test** that calls `gui.main(["gui.py", "--smoke-test"])` with patched `QApplication` and `OxfordToNotionWindow`. Assert that it:
  - creates the application and window;
  - passes `start_update_check=False` and `enable_recent_sync=False`;
  - does not call `show()` or `exec()`;
  - returns `0`.

`enable_recent_sync` is introduced by the approved Recent-sync plan and prevents network work during packaging checks.

- [ ] **Prove it fails**:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_gui_smoke.py -q
```

- [ ] **Refactor only `main()`** to this contract:

```python
def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    app = QApplication.instance() or QApplication(args)
    smoke_test = "--smoke-test" in args
    window = OxfordToNotionWindow(
        start_update_check=not smoke_test,
        enable_recent_sync=not smoke_test,
    )
    if smoke_test:
        return 0
    window.show()
    return app.exec()
```

The module guard must become `raise SystemExit(main())`.

- [ ] **Extend the Windows build smoke check.** After PyInstaller succeeds, `build_app.bat` must run:

```bat
"dist\Oxford to Notion.exe" --smoke-test
if errorlevel 1 exit /b 1
```

Update `tests/test_build_scripts.py` to require that invocation and its exit-code check.

- [ ] **Verify and commit**:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_gui_smoke.py tests/test_build_scripts.py -q
git add gui.py build_app.bat tests/test_gui_smoke.py tests/test_build_scripts.py
git commit -m "Add packaged application smoke test"
```

---

### Task 3: Add deterministic macOS build scripts

**Files:** Create `requirements-macos-build.txt`, `scripts/build_macos_app.sh`, `scripts/package_macos_dmg.sh`, `tests/test_macos_build_files.py`; modify `.gitignore`.

- [ ] **Write static contract tests first.** `tests/test_macos_build_files.py` must assert:
  - build dependencies pin `PySide6-Essentials`, `shiboken6`, and `pyinstaller`;
  - the build script uses `iconutil -c icns`, PyInstaller, the colon-form `--add-data`, `--smoke-test`, and ad-hoc `codesign`;
  - the build script never mentions `.env`;
  - the packaging script creates an `/Applications` symlink, calls `hdiutil create`, and creates a SHA-256 file.

- [ ] **Prove the tests fail because the files are absent**:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_macos_build_files.py -q
```

- [ ] **Pin the packaging environment** in `requirements-macos-build.txt`:

```text
-r requirements.txt
PySide6-Essentials==6.11.1
shiboken6==6.11.1
pyinstaller==6.21.0
```

- [ ] **Implement `scripts/build_macos_app.sh`.** It must use `set -euo pipefail`, quote every path, and perform these steps in order:
  1. resolve repository root;
  2. recreate only `work/macos/AppIcon.iconset`;
  3. use `sips` to generate Apple's 16, 32, 64, 128, 256, 512, and 1024 pixel iconset names from `assets/app-icon.png`;
  4. create `work/macos/app-icon.icns` using `iconutil -c icns`;
  5. remove only `build/Oxford to Notion` and `dist/Oxford to Notion.app`;
  6. run `python -m PyInstaller --noconfirm --clean --onedir --windowed --icon work/macos/app-icon.icns --add-data "assets/app-icon.png:assets" --name "Oxford to Notion" gui.py`;
  7. run `dist/Oxford to Notion.app/Contents/MacOS/Oxford to Notion --smoke-test`;
  8. run `codesign --force --deep --sign -` and then `codesign --verify --deep --strict` on the app.

- [ ] **Implement `scripts/package_macos_dmg.sh`.** It must fail if the app is absent, recreate only `work/macos/dmg-stage`, copy the app with `ditto`, link `/Applications`, create `release/Oxford-to-Notion-macOS-arm64.dmg` using compressed read-only `UDZO`, and write the adjacent `.sha256` using `shasum -a 256`.

- [ ] **Ignore only generated output**:

```gitignore
work/macos/
release/Oxford-to-Notion-macOS-arm64.dmg
release/Oxford-to-Notion-macOS-arm64.dmg.sha256
```

- [ ] **Verify and commit**:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_macos_build_files.py -q
git add requirements-macos-build.txt scripts/build_macos_app.sh scripts/package_macos_dmg.sh tests/test_macos_build_files.py .gitignore
git commit -m "Add macOS ARM64 packaging scripts"
```

---

### Task 4: Build a private ARM64 artifact in GitHub Actions

**Files:** Create `.github/workflows/macos-arm64-build.yml`; modify `tests/test_macos_build_files.py`.

- [ ] **Add a failing workflow contract test** requiring:
  - `workflow_dispatch` only;
  - `runs-on: macos-15`;
  - `permissions: contents: read`;
  - Python 3.13 through `actions/setup-python@v5`;
  - the complete pytest suite;
  - both packaging scripts;
  - `lipo -info`, DMG mounting, and mounted-app smoke test;
  - `actions/upload-artifact@v4` with 14-day retention;
  - no Release-publishing action.

- [ ] **Prove the workflow test fails**:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_macos_build_files.py -q
```

- [ ] **Create the workflow** with one 30-minute `macos-15` job. Install `requirements-macos-build.txt`, run tests, build the app and DMG, verify the executable is ARM64, mount the DMG under `work/macos/mounted`, smoke-test the mounted executable, detach in an `always()` step, and upload only the DMG plus checksum as `Oxford-to-Notion-macOS-arm64`. Do not use repository secrets or create a Release.

- [ ] **Verify and commit**:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_macos_build_files.py -q
git add .github/workflows/macos-arm64-build.yml tests/test_macos_build_files.py
git commit -m "Build private macOS ARM64 artifact in CI"
```

---

### Task 5: Document the M-series test installation

**Files:** Modify `README.md`, `README.en.md`, `CHANGELOG.md`, `tests/test_readme.py`.

- [ ] **Add failing documentation tests** requiring both READMEs to mention Apple silicon (M1/M2/M3/M4), the private Actions artifact, dragging the app to Applications, first launch by right-click/Open, the unsigned-build warning, separate local Notion configuration, and Notion-backed Recent sync with local fallback.

- [ ] **Prove the checks fail**:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_readme.py -q
```

- [ ] **Update both READMEs** near the Windows installer section with six beginner steps:
  1. download and unzip the Actions artifact;
  2. open the DMG;
  3. drag the app to Applications;
  4. first launch via right-click → Open because the free build is not notarized;
  5. paste the Notion token and database URL in Mac Settings;
  6. open Recent and allow a brief Notion synchronization.

State that this is an M-series test artifact, not a final public Release. Add a bilingual `Unreleased` changelog entry for the ARM64 test build and synced Recent behavior.

- [ ] **Verify and commit**:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_readme.py -q
git add README.md README.en.md CHANGELOG.md tests/test_readme.py
git commit -m "Document macOS ARM64 test installation"
```

---

### Task 6: End-to-end verification and M3 handoff

**Files:** Verification only; no planned source changes.

- [ ] **Run all Windows tests**:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp "$env:TEMP\oxford-to-notion-macos-tests"
```

- [ ] **Build and smoke-test Windows**:

```powershell
.\build_app.bat --no-pause
& ".\dist\Oxford to Notion.exe" --smoke-test
```

- [ ] **Review scope and secret safety**:

```powershell
git status --short
git diff --check origin/main...HEAD
git log --oneline origin/main..HEAD
git grep -n "ntn_" -- . ":(exclude).env" ":(exclude)docs/superpowers/specs/*" ":(exclude)docs/superpowers/plans/*"
```

Expected: no token match and no unrelated changes.

- [ ] **Push and trigger the private build**:

```powershell
git push origin main
gh workflow run macos-arm64-build.yml --ref main
gh run list --workflow macos-arm64-build.yml --limit 1
gh run watch --exit-status
```

- [ ] **Download the artifact**:

```powershell
New-Item -ItemType Directory -Force -Path work\macos-artifact | Out-Null
gh run download --name Oxford-to-Notion-macOS-arm64 --dir work\macos-artifact
Get-ChildItem -LiteralPath work\macos-artifact
```

Expected: one DMG and its SHA-256 file. Do not publish a Release.

## M3 Acceptance Gate

The user verifies on the MacBook that:

- right-click → Open launches without a Terminal window;
- icon, Chinese/English switching, Import, Recent, and Settings render correctly;
- Notion connection testing succeeds;
- importing creates or updates the intended page;
- Recent retrieves the latest Notion history and falls back to cache offline;
- Windows sees the same recent word after its next Recent refresh.

Only after this checklist passes should a separate release task publish the DMG publicly.

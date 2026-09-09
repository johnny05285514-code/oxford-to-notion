# Unified releases and assisted in-app updates

Date: 2026-09-09
Status: approved design, awaiting implementation plan
Target release: v1.5.3

## Goal

Oxford to Notion must use one version number everywhere, publish Windows and macOS together, show the installed version in Settings, and let users download a verified update from inside the app. Installation remains user-controlled.

The first release containing this system will be v1.5.3. Existing v1.5.2 installations still require one manual update. From v1.5.3 onward, the assisted in-app update flow applies.

## User experience

Settings gains an **About and updates** group containing:

- product name;
- `Current version: v1.5.3` / `当前版本：v1.5.3`;
- a **Check for updates** button;
- an update status line and progress indicator when needed.

The app keeps its existing once-per-day background check. It never downloads or installs an update without a click from the user. A manual check ignores the daily throttle and reports one of these states:

- checking;
- up to date;
- update available;
- downloading with progress;
- downloaded and verified;
- download, integrity, or launch failure.

When an update is available, the existing main-page update banner and the Settings group both offer **Download update**.

After verification:

- On Windows, **Install now** launches the visible NSIS installer. The app quits only after the installer starts successfully.
- On an Apple silicon Mac, **Open installer** opens the DMG. The app explains how to drag Oxford to Notion into Applications and choose Replace. It does not attempt to replace itself.
- On an unsupported platform or Mac architecture, the app opens the GitHub Release page instead of downloading an incompatible file.

All new text is available in Simplified Chinese and English. Changing language updates the version and update controls without resizing the window.

## Single version source

Add a tracked `version.json` file containing one semantic version string. No production component may contain a separately maintained release number.

A small `app_version.py` module reads and validates this file and exposes the current version to Python code. PyInstaller bundles `version.json` in Windows and macOS packages.

Build tools read the same file:

- `update_checker.py` imports the version through `app_version.py`.
- The Windows build passes the value to NSIS as `APP_VERSION`; `installer.nsi` rejects a missing value and contains no hard-coded release version.
- The Windows installed icon uses a stable filename, `app-icon.ico`, rather than a versioned filename.
- The macOS build writes the value to `CFBundleShortVersionString` and a numeric equivalent to `CFBundleVersion`.
- README download examples and version-specific release notes are validated against `version.json` during a release.

Invalid or missing version data fails tests and packaging instead of silently falling back to an old version.

## Unified release workflow

Replace separate manual packaging steps with one GitHub Actions workflow named **Publish Windows and macOS release**. It is manually dispatched so publishing remains intentional.

The workflow performs these stages:

1. Read and validate `version.json`; ensure the matching `vX.Y.Z` tag and public Release do not already exist.
2. Run the full test suite.
3. Build the Windows installer and SHA-256 file on a Windows runner.
4. Build the Apple silicon DMG and SHA-256 file on an ARM64 macOS runner.
5. Verify the Windows version metadata, packaged startup, macOS bundle version, ARM64 executable, DMG mount, packaged startup, filenames, and both checksums.
6. Create a draft GitHub Release, upload all four files, and verify the asset list.
7. Publish the Release and mark it latest only after every required asset is present.

If either platform fails, no public Release is created. If the final upload stage fails, the Release remains a draft and users continue seeing the previous latest version.

Each release contains exactly these platform assets:

```text
Oxford-to-Notion-Setup-X.Y.Z.exe
Oxford-to-Notion-Setup-X.Y.Z.exe.sha256
Oxford-to-Notion-macOS-arm64.dmg
Oxford-to-Notion-macOS-arm64.dmg.sha256
```

The workflow uses only official GitHub actions and the GitHub CLI. Release notes remain bilingual and are prepared in a version-specific Markdown file before dispatch.

## Update metadata and platform selection

Extend the existing GitHub Releases check so `UpdateInfo` contains the release version, release page, platform package URL, checksum URL, expected filename, and download size.

Asset selection is strict:

- Windows accepts only `Oxford-to-Notion-Setup-X.Y.Z.exe` and its matching checksum.
- macOS accepts only `Oxford-to-Notion-macOS-arm64.dmg` and its matching checksum when `platform.machine()` reports ARM64.
- URLs must be HTTPS and originate from the configured Oxford to Notion GitHub repository release metadata.
- Missing, duplicate, malformed, draft, or prerelease assets make the release unavailable to the in-app downloader.

The existing daily cache stores only validated, non-sensitive metadata. A new app version re-evaluates cached version data against its own current version, so an equal or older cached release is never shown as an update.

## Download and integrity verification

Add an update download service independent of the GUI. It:

1. creates a platform-appropriate update cache directory;
2. downloads the checksum file and package using streaming requests and bounded timeouts;
3. enforces a 200 MB maximum package size;
4. computes SHA-256 while writing to a uniquely named temporary file;
5. requires an exact checksum entry for the expected filename;
6. atomically renames the file only after the checksum matches;
7. returns a verified local path to the GUI.

Windows uses `%LOCALAPPDATA%\Oxford to Notion\Updates`. macOS uses `~/Library/Caches/Oxford to Notion/Updates`. The Notion Token, database identifier, history, and settings are never read by the downloader or included in update requests.

Old temporary downloads are removed on the next startup. A verified package may be reused if its filename and checksum still match.

## Error handling and safety

- Network failure leaves the installed app unchanged and offers Retry or View release page.
- An absent or malformed checksum prevents installation.
- A checksum mismatch deletes the temporary package, reports that verification failed, and never launches it.
- A full disk, unwritable cache folder, timeout, or interrupted download produces a localized message and preserves the current version.
- Failure to launch the Windows installer does not quit the app.
- Failure to open the macOS DMG leaves the downloaded file in place and offers Retry or Open download folder.
- Only a direct user action can launch an installer.

This feature does not bypass Windows SmartScreen or macOS Gatekeeper. Until commercial code signing and Apple notarization are added, the app continues to explain the possible Unknown Publisher and Privacy & Security prompts.

## Code boundaries

- `version.json`: single release number.
- `app_version.py`: load and validate the current version.
- `update_checker.py`: query and validate release metadata and choose the platform asset.
- `update_downloader.py`: download, checksum, cache, and return a verified package.
- `gui.py`: display version, update states, progress, and platform-specific install action.
- `app_paths.py`: platform-specific update cache location.
- `i18n.py`: Chinese and English labels and errors.
- `installer.nsi` and build scripts: consume the shared version and use stable installed resource names.
- `.github/workflows/release.yml`: build, verify, and publish both systems together.

The downloader and release workflow remain separate from Oxford lookup, Notion import, Recent synchronization, and user settings.

## Testing and acceptance criteria

Unit tests cover:

- valid and invalid `version.json` values;
- comparison with older, equal, and newer releases;
- strict platform and architecture asset selection;
- malformed, duplicate, missing, draft, and prerelease assets;
- checksum parsing, matching, mismatch, truncated downloads, timeouts, size limits, and write failures;
- safe reuse and cleanup of downloaded files;
- installer or DMG launch success and failure without invoking real installers.

GUI tests cover both languages, manual re-check, daily background checks, progress states, retry behavior, current version display, minimum-window layout, and language switching without resizing.

Packaging tests prove that:

- Python, NSIS, Windows metadata, macOS bundle metadata, filenames, and Release tag all use the same version;
- neither package contains `.env`, history, cached updates, or Notion credentials;
- Windows and macOS packaged startup checks pass;
- a Release cannot become public unless all four assets and their verified checksums are present.

Before publishing v1.5.3, acceptance requires real Windows and M3 Mac tests using locally staged, checksum-verified v1.5.3 packages to prove the download, launch, DMG-open, and replace instructions. The first production cross-version test occurs when v1.5.3 detects and installs v1.5.4; its result must be recorded before later releases rely solely on the automated workflow.

## Non-goals

- silent or unattended installation;
- bypassing operating-system security warnings;
- Intel Mac support;
- delta patches;
- rollback automation;
- background downloads;
- automatic Notion configuration migration.

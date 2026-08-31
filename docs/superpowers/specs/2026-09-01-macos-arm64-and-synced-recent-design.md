# macOS ARM64 and Synced Recent Design

Date: 2026-09-01
Status: Approved in chat; awaiting final document review

## Purpose

Add a free personal macOS build for an Apple M3 MacBook while preserving the existing Windows app. The macOS app must be downloadable as an unsigned Apple Silicon DMG, require no development tools for the end user, and share Recent history across Windows and macOS through the user's existing Notion database.

## Goals

- Produce a native ARM64 `Oxford to Notion.app` and `Oxford-to-Notion-macOS-arm64.dmg` on GitHub Actions.
- Keep the existing PySide6 interface and shared Python application logic.
- Preserve the current Windows build, installer, configuration, and user data behavior.
- Store macOS configuration under `~/Library/Application Support/Oxford to Notion`.
- Treat Notion as the authoritative source for the 100 most recently imported words.
- Show cached Recent data immediately and refresh it in the background.
- Let a non-technical user install the app by dragging it into Applications.
- Keep the Notion token and database URL out of Git, build artifacts, and GitHub Actions logs.

## Non-goals

- Rewriting the app in SwiftUI.
- Publishing through the Mac App Store.
- Apple Developer ID signing or notarization in the first release.
- Automatically migrating a Windows token to macOS.
- Synchronizing arbitrary local files between computers.
- Adding automatic in-app installation of updates.
- Building an Intel macOS package in the first iteration.

## Chosen Approach

Continue using PySide6 and PyInstaller. A GitHub Actions workflow running on the standard ARM64 `macos-15` runner will test the project, build an application bundle, create an ad-hoc signature, package a DMG, verify its architecture and contents, and upload it as a private-to-the-workflow artifact for user testing.

This approach reuses the existing GUI and application services. It requires fewer platform-specific changes than a native rewrite and avoids asking the user to install Python or use Terminal on the MacBook.

## Platform-aware Application Data

`app_paths.app_directory()` will select a user-writable directory by platform when running as a frozen application:

- Windows: `%APPDATA%\Oxford to Notion` (unchanged).
- macOS: `~/Library/Application Support/Oxford to Notion`.
- Source checkout: the repository directory remains the default so existing development workflows continue to work.

The selected directory continues to contain `.env`, `history.json`, and `update-state.json`. Directory creation remains lazy and occurs only when a file must be written.

The macOS app will not read the Windows `.env`. On first launch, the existing setup wizard asks for the Notion token and database URL, tests the connection, and saves them only in the macOS application-data directory.

## Synced Recent Data

### Source of truth

The Notion database is authoritative for Recent history. The app will request at most 100 pages sorted by the `Added Date` property in descending order. Each result will be converted to the existing history-record shape containing only:

- word
- Notion page URL
- Oxford source URL
- added date

No token, definition text, examples, or Oxford HTML will be added to the cache.

### Refresh behavior

1. At startup, the app reads `history.json` and renders the Import-page preview and Recent page immediately.
2. If valid Notion settings exist, a background worker requests the latest 100 records.
3. A successful response atomically replaces the local cache and refreshes both views on the GUI thread.
4. Navigating to Recent requests a refresh when the last attempt is more than 60 seconds old.
5. A successful import updates the local cache immediately, then schedules a Notion refresh.
6. Re-importing an existing word updates its existing Notion page and its `Added Date`, moving it to the top on both computers.

Only one Recent synchronization request may run at a time. Repeated navigation while a request is active does not create duplicate requests.

### Offline behavior

If the network, Notion API, credentials, permissions, schema, or response parsing fails:

- Existing cached records remain visible and usable.
- Import and search controls remain responsive.
- A localized, non-blocking message says that cached records are being shown because synchronization is temporarily unavailable.
- The technical exception is not displayed to the user, but may be retained for optional diagnostics.
- A later navigation or successful import can retry synchronization.

An empty cache plus a failed first synchronization shows an empty-state explanation rather than an error dialog.

### Search and link behavior

The current case-insensitive substring search remains unchanged. For example, `mit` matches `emitted`. Synced records use the existing setting that chooses whether a Recent item opens Notion or Oxford.

## Notion Integration Changes

The Notion layer will expose a focused method for reading recent records rather than letting GUI code construct API queries. It will:

- Reuse the existing token and normalized database identifier.
- Query no more than 100 pages.
- Sort by `Added Date` descending.
- Safely extract the title/Word, Source URL, page URL, and date.
- Ignore malformed individual records without failing the whole refresh.
- Translate authorization, missing-database, schema, rate-limit, network, and generic API failures into existing user-facing error categories.

The existing duplicate-update path will continue preserving user-authored Notion page blocks. Only app-managed properties and app-managed content are updated. Refreshing Recent must never modify Notion.

## GUI Integration

A dedicated background worker performs the Notion read so the Qt event loop is never blocked. Signals deliver either normalized records or a categorized failure to the main window.

The Import page continues showing five recent words. The Recent page continues showing up to 100 and retains its visible search field. The only new visible state is a small localized synchronization notice when cached data is used after a failed refresh. No modal dialog appears for background synchronization failures.

All new user-visible strings will be available in Simplified Chinese and English through the existing language system.

## macOS Packaging

### App bundle

The macOS build will use PyInstaller in windowed, one-directory app-bundle mode. It will include:

- Application Python modules and dependencies.
- Qt frameworks and plugins selected by PyInstaller.
- `assets/app-icon.png` and a generated `assets/app-icon.icns`.
- Bundle metadata naming the product `Oxford to Notion`.

The workflow will generate `.icns` from the existing high-resolution PNG using macOS `sips` and `iconutil`. The generated `.icns` remains a build artifact and is not committed.

### Free personal signature

The workflow will apply an ad-hoc signature with `codesign --sign -`. This validates bundle integrity but is not Apple Developer ID signing or notarization. Gatekeeper may therefore require the user to right-click the app, choose Open, and confirm on first launch.

No certificate, Apple ID, password, or signing secret is required or stored.

### DMG layout

The DMG will contain:

- `Oxford to Notion.app`
- A link to `/Applications`

The user installs by dragging the app onto Applications. The initial DMG is uploaded as a GitHub Actions artifact and is not attached to a public Release until the M3 MacBook test passes.

## GitHub Actions Workflow

The new workflow will be manually triggered with `workflow_dispatch` and will use `macos-15`, which is an ARM64 standard runner for this public repository.

The workflow will:

1. Check out the exact commit.
2. Install a supported Python version and project dependencies in a clean virtual environment.
3. Run the complete automated test suite.
4. Generate the `.icns` icon.
5. Build the `.app` bundle.
6. Run a frozen-app smoke test that imports Qt, constructs the application, avoids network calls, and exits successfully.
7. Apply and verify the ad-hoc signature.
8. Verify the main executable is ARM64 using macOS binary inspection tools.
9. Create the DMG with `hdiutil`.
10. Mount the DMG read-only, confirm the app is present, then detach it.
11. Produce a SHA-256 checksum.
12. Upload the DMG and checksum as an Actions artifact with a 14-day retention period.

The workflow receives no Notion secrets and must not access `.env`.

## Frozen-app Smoke Test

The GUI entry point will accept an internal `--smoke-test` argument. In this mode it will:

- Import the required Qt modules.
- Create `QApplication` and the main window without showing it.
- Skip update checks, Oxford requests, Notion requests, and user-data writes.
- Exit with code zero after successful construction.

The mode exists only to validate packaged runtime integrity. It will be usable for both Windows and macOS builds so future packaging failures are detected before distribution.

## Testing

### Unit tests

- Windows frozen paths remain unchanged.
- macOS frozen paths use Application Support.
- Recent responses normalize and sort correctly.
- Malformed Notion records are skipped.
- A maximum of 100 records is requested and stored.
- Offline failures preserve the prior cache.
- Atomic cache writes do not leave temporary files.
- Duplicate refresh requests are suppressed.
- Localized sync messages exist in Chinese and English.
- Existing substring search works with synced records.
- Smoke-test mode avoids external I/O.

### Windows regression testing

Run the complete suite on Windows and rebuild the Windows executable. Verify that the installed Windows app still opens, existing private files remain unchanged, and no macOS-only asset or command enters the Windows package.

### macOS CI verification

- Complete tests pass on ARM64 macOS.
- The frozen smoke test exits successfully.
- `codesign --verify` succeeds for the ad-hoc signature.
- The main Mach-O executable reports ARM64.
- The DMG mounts and contains the expected app.
- The checksum matches the produced DMG.

### M3 acceptance test

The user will verify on the M3 MacBook:

- DMG opens and the app can be copied to Applications.
- The documented right-click Open flow succeeds.
- The icon and main window render correctly.
- Chinese and English switching works.
- Setup wizard saves and tests Notion settings.
- Importing a word creates or updates the correct Notion page.
- Windows-originated Recent records appear on Mac.
- A Mac import appears in Windows Recent after refresh.
- Search and Recent link targets work.
- Relaunching retains configuration and cache.

## Documentation and Release Flow

README and README.en will gain short, beginner-oriented macOS sections covering:

- Downloading the ARM64 DMG.
- Dragging the app into Applications.
- The first-launch right-click Open step.
- Re-entering Notion settings on the Mac.
- The meaning of local caching and Notion-backed Recent sync.
- The unsigned personal-build limitation.

After the M3 acceptance test passes, the DMG and checksum will be attached to the next public GitHub Release alongside the Windows installer. The release notes will identify the macOS artifact as Apple Silicon only and unsigned/not notarized.

## Security and Privacy

- No `.env`, token, database URL, or personal history file is committed or uploaded as a build artifact.
- GitHub Actions builds only from repository content and receives no Notion secrets.
- The macOS token remains under the current user's Application Support directory.
- Synced Recent data is read only from the database already authorized for the user's Notion Integration.
- Oxford usage remains personal and low frequency; Recent synchronization does not contact Oxford.

## Acceptance Criteria

The implementation is complete when:

1. All automated tests pass on Windows and ARM64 macOS.
2. Windows behavior and private files are preserved.
3. GitHub Actions produces a verified ARM64 DMG and checksum without secrets.
4. The app stores macOS data in Application Support.
5. Recent history synchronizes through Notion with responsive cached fallback.
6. The packaged smoke test succeeds.
7. The user completes the M3 acceptance test.
8. Only after that approval is the DMG published in a public GitHub Release.

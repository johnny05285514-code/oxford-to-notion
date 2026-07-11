# Update Reminder, Import History, and Demo GIF Design

## Goal

Extend the desktop app with a quiet update reminder, a compact list of recent successful imports, and a README demonstration GIF without disrupting the current single-column import workflow.

## Main-page layout

Use the approved compact layout A.

- Keep the title, language button, Settings button, word input, import button, and status area in their current positions.
- Show an update banner below the status area only when a newer release exists.
- Show `最近导入` / `Recently imported` beneath the banner area.
- Render up to five recent words as compact buttons in one wrapping row.
- Hide the recent-import section when there is no history.
- Preserve the current minimum window size; the new content must fit without horizontal scrolling.

## Import history

- Save history locally as `history.json` in the existing application data directory next to `.env`.
- Each item contains only `word`, `page_url`, and an ISO-8601 `imported_at` timestamp.
- Store at most five items.
- A successful import adds the item to the front.
- Importing the same normalized word again removes its older item and moves the latest result to the front.
- A failed import does not modify history.
- Clicking a history word opens its stored Notion page URL in the default browser.
- Invalid JSON, invalid records, or unsafe non-HTTP(S) URLs are ignored. A damaged history file must never prevent the app from opening or importing.
- History stays local and is never included in builds, installers, Git, or update requests.

## Update reminder

- The installed application version is `1.3.0`; the next feature release will be `1.4.0`.
- Query `https://api.github.com/repos/johnny05285514-code/oxford-to-notion/releases/latest` in a background worker after the main window opens.
- Send a descriptive User-Agent and use a short network timeout.
- Compare numeric semantic versions after removing an optional leading `v`.
- Ignore draft and prerelease releases.
- Cache the last successful check time and result in `update-state.json` in the local application data directory.
- Perform at most one network check every 24 hours. Reuse the cached result inside that interval.
- Network, rate-limit, malformed-response, and GitHub API failures are silent; they do not change import status or show an error dialog.
- When a newer stable release exists, show a compact blue banner with the localized message and `查看更新` / `View update` action.
- Clicking the action opens the HTTPS release page in the default browser.
- Do not download, install, or execute updates automatically.

## Localization

Add Simplified Chinese and English text for:

- Recent-import section title and button tooltips.
- Update-available message and action.
- Any nonblocking history-save warning that is surfaced in development logs; no technical error is shown to normal users.

Changing language immediately retranslates the visible update banner and history heading without changing stored words or URLs.

## Demo GIF

- Record only after the feature build passes all tests and the final layout is installed.
- Use a test or demonstration Notion target with no visible Token, database ID, personal page titles, notifications, or unrelated desktop content.
- Show: open app, enter a sample word, import successfully, and observe the word appear in Recent imports.
- Keep the GIF short, crop it to the app window, and optimize it for a reasonable GitHub README file size.
- Store it at `assets/demo.gif` and embed it in both `README.md` and `README.en.md`.

## Components

- `history_store.py`: validates, reads, deduplicates, and atomically writes recent imports.
- `update_checker.py`: version parsing/comparison, GitHub request, cache policy, and safe result model.
- `gui.py`: background update worker, compact banner, recent-import buttons, browser opening, and retranslation.
- `i18n.py`: new Chinese and English message keys.
- `app_paths.py`: local paths for `history.json` and `update-state.json`.
- Tests isolate all local files and network calls; no test contacts Oxford, Notion, or GitHub.

## Testing and acceptance

- History tests cover missing/corrupt files, URL validation, five-item limit, duplicate movement, and atomic persistence.
- Update tests cover version ordering, cached checks, stale checks, stable-release filtering, malformed JSON, timeout, and silent failure.
- GUI tests cover hidden empty history, new history after successful import, clickable Notion links, hidden update banner, visible newer-version banner, browser action, and immediate Chinese/English retranslation.
- The full existing suite remains green.
- The installer contains no `.env`, `history.json`, `update-state.json`, Token, or Database ID.
- A silent upgrade preserves `.env` and existing local history.
- The installed v1.4.0 app launches normally and the README GIF displays on GitHub.

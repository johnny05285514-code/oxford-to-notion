# Recent history search design

## Goal

Make the Recent page practical when the local import history contains many words, without changing Notion data, import behavior, or the five-item summary on the Import page.

## User experience

- Add one search input below the Recent page subtitle and above the scrollable history list.
- The input filters while the user types; there is no separate search button.
- Matching is case-insensitive and uses substring matching. For example, `mit` matches `emitted`.
- Clearing the input restores the complete local history list.
- When there are saved words but no search result, show a localized no-match message.
- Result buttons keep the existing behavior: they open Notion or Oxford according to the user's Settings preference.

## Scope

- Search only the Recent page.
- Search only the word text held in the existing local history list.
- Do not add cloud search, sorting, tags, deletion, or changes to `history.json`.

## Implementation outline

- Keep the loaded history list on the window after `refresh_history`.
- Add a bilingual `QLineEdit` search field and connect text changes to a small filtering method.
- Rebuild only the Recent list from the matching items; the Import page's recent-five grid stays unchanged.
- Reuse the existing history-button factory, URL selection, and tooltip behavior.

## Error and empty states

- Empty history: retain the existing localized empty-history message.
- Non-empty history with zero matches: display a separate localized no-match message.
- Whitespace-only input behaves as an empty search.

## Verification

- Automated tests prove case-insensitive substring matching, clearing the search, the no-match state, and preservation of the existing click target.
- Existing full test suite and Windows package build must pass.

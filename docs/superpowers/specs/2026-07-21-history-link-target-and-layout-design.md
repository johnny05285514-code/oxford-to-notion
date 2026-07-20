# Recent History Link Target and Layout Design

## Goal

Add a setting that lets users choose whether a recently imported word opens its Notion page or its Oxford Learner's Dictionaries page. The choice applies to all existing and future history items. Also prevent the English success state and a full five-item history from wrapping into a clipped or overlapping layout.

## User experience

The Settings page gains one bilingual dropdown labelled "Open recent imports in" / "最近导入打开方式" with two choices:

- Notion
- Oxford Learner's Dictionaries

The default remains Notion so an upgrade does not unexpectedly change existing behaviour. Saving Settings persists the selection locally. Changing the selection affects every history button immediately after returning to the main page.

The large success-state button remains "Open in Notion" because it is a direct link to the page that was just created or updated. Only the buttons in the "Recently imported" section use the new preference.

## Link resolution and compatibility

No history-file migration is required. History continues to store the canonical imported word and its Notion page URL.

When Notion is selected, a history button opens its stored Notion page URL exactly as it does today.

When Oxford is selected, the app creates an official Oxford direct-search URL from the canonical history word, using URL encoding. Oxford then resolves that word to its definition page. This works for both old and new history entries, including entries that originated from inflected searches such as `emitted` resolving to `emit`.

The preference is stored in the existing local `.env` file as a non-secret application setting. Missing or unrecognised values safely fall back to Notion.

## Layout behaviour

The success-status row will give its text label enough horizontal space to keep normal Chinese and English success messages on one line. Word wrapping remains available for unusually long words or narrow/high-scaling displays.

The main page will re-check its required content height after:

- a successful import;
- history refresh;
- language change; and
- update-banner changes.

The existing minimum window size remains unchanged. Normally the wider status row prevents extra height. If content genuinely needs more vertical room, the window grows only by the missing amount so the second history row and footer cannot overlap or be clipped.

The history section retains up to five items in a three-column grid and keeps a stable gap between its second row and the footer.

## Error handling

Opening an Oxford history link does not make an Oxford request inside the app; it hands the validated HTTPS URL to the system browser. Invalid setting values fall back to Notion. Existing validation for stored Notion history URLs remains unchanged.

## Verification

Automated tests will verify:

- the new preference defaults to Notion;
- both valid choices persist and reload;
- invalid values fall back to Notion;
- existing and new history items open Notion when Notion is selected;
- existing and new history items use an encoded Oxford direct-search URL when Oxford is selected;
- the large success button still opens Notion;
- Chinese and English success states with five history items leave the footer fully below the history grid;
- switching language and refreshing history trigger content fitting; and
- the complete existing test suite still passes.

## Release scope

After verification, publish this as the next patch release, update the changelog and README where the setting is documented, build the Windows installer, and upgrade the local installed copy while preserving the user's `.env` settings and history. The release will not change Notion database fields, Oxford parsing, import semantics, or history capacity.

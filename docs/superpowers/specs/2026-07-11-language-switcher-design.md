# Language Switcher Design

## Goal

Add a scalable language selector to the desktop app so users can switch the complete interface between Simplified Chinese and English without restarting the application.

## User interface

- Place a compact language button immediately to the left of the Settings button on the main page.
- The button shows a globe symbol and the active language, such as `🌐 中文` or `🌐 English`.
- Clicking it opens a menu containing `简体中文` and `English`.
- The selected item is visibly checked.
- Keep the menu structure data-driven so more languages can be added later without redesigning the header.
- The same language selector remains available on the Settings page and first-run setup wizard so the user is never trapped in an unfamiliar language.

## Language selection

- On first launch, detect the Windows UI language.
- Select Simplified Chinese only when the system language is Chinese.
- Select English for English, unsupported, missing, or unrecognized system languages.
- Save an explicit user choice in the application's existing local `.env` settings as `APP_LANGUAGE`.
- A saved choice takes precedence over system detection on later launches.

## Translation scope

Switch all application-owned text immediately:

- Main page labels, placeholders, buttons, status messages, and success/error messages.
- Settings page labels, buttons, validation messages, and connection-test messages.
- All five first-run setup wizard steps, descriptions, navigation, and connection-test messages.
- Friendly Oxford, network, configuration, parser, and Notion error messages shown by the GUI.

Do not translate Oxford words, definitions, examples, parts of speech, or other dictionary content.

## Architecture

- Add a small `i18n.py` module containing supported-language metadata, system-language detection, and Chinese/English message dictionaries.
- Address messages with stable keys instead of scattering language checks throughout widgets.
- Widgets expose a `retranslate_ui()` method that updates their visible text in place.
- The main window owns the active language, updates all current pages after selection, and persists it through `settings_store.py`.
- Background workers continue returning stable application errors. The GUI converts known errors to friendly localized messages at display time, with a localized generic fallback for unexpected errors.

## Error handling

- Missing or invalid `APP_LANGUAGE` falls back to system detection, then English.
- Missing translation keys fall back to English rather than displaying an empty label.
- A failure to save the language choice changes the interface for the current session and shows a localized warning; it must not block importing words.

## Testing

- Unit-test system-language detection and unsupported-language fallback.
- Unit-test language preference read/write without exposing or changing Notion credentials.
- GUI-test the language menu location, available choices, immediate main-page switching, and persistence.
- GUI-test Settings and Setup Wizard retranslation.
- Test representative friendly Oxford/network/Notion errors in both languages.
- Run the complete existing test suite and rebuild the Windows installer before release.

## Release acceptance

- A new user on Chinese Windows starts in Chinese.
- A new user on any other or unrecognized system language starts in English.
- Switching languages updates the visible application immediately and survives restart.
- Existing Notion configuration remains unchanged.
- The installer upgrades the current version without removing local settings.

# v1.4.1 Reliability Design

## Goal

Prevent repeat imports from deleting personal Notion notes, reject stale Notion connection-test results, and present friendly errors for all common Notion network failures.

## Safe Notion content ownership

New Oxford page content is stored inside a top-level toggle named `Oxford content — managed by Oxford to Notion`. This toggle is the only page-body block the app owns.

For an existing v1.4.0 page with no managed toggle, the first repeat import preserves every existing block and appends a new managed toggle. The old Oxford content may therefore appear once beside the new managed content, but personal notes cannot be mistaken for generated content or deleted.

For a page that already has managed toggles, an update uses a safe replacement order:

1. Create and fully populate a new managed toggle.
2. Update the database properties.
3. Delete only the older managed toggles.

If creating the replacement fails, the incomplete new toggle is removed best-effort and the old managed content remains. If cleanup fails, duplicate managed toggles are safer than data loss and are cleaned on a later successful retry.

## Connection-test correctness

The setup wizard records the exact Token and database value submitted for a test. A successful callback is accepted only if the current fields still match those values. Editing either field invalidates the result. The same protection is applied to the Settings page status.

## Network errors and dependencies

`httpx.RequestError` and Notion `HTTPResponseError` are converted to the existing user-facing Notion connection/write errors. `httpx` becomes an explicit dependency, and `notion-client` is fixed to the verified `2.7.0` version.

## Release scope

Version references become `1.4.1`. A bilingual `CHANGELOG.md` and release notes explain the safe-update migration. No analytics, schema change, token migration, or unrelated UI redesign is included.

## Verification

- Regression tests fail on v1.4.0 behavior before implementation.
- Unit tests verify legacy blocks and personal notes are preserved.
- Unit tests verify only old managed toggles are deleted after a successful replacement.
- Unit tests verify stale connection success cannot enable saving.
- Unit tests verify transport errors become friendly Notion errors.
- Existing tests, a real read-only Oxford lookup, installer build, secret scan, and checksum verification must pass before release.

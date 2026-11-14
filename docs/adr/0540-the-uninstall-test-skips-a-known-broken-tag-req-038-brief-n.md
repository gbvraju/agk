# ADR-0540: The uninstall test skips a known-broken tag

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: brief #1278, brief #1273, brief #1257, issue #1256, PR #1258, ADR-0539, SPEC-0028 rule 4
- Requirements: REQ-038

Protected classes: `tests/kit_dev/`

## Context

With the corrected file table of release 0.64.4 (#1258), `test_a_released_install_round_trip_lists_every_kit_file_delete`
picks 0.64.3 as the newest release row with a commit, and that tag refuses its own install (issue #1256). ADR-0539
made the one list `KNOWN_BROKEN_TAGS` for the upgrade test; this ADR extends its use to the uninstall test.

## Decision

1. `newest_with_commit()` in `tests/kit_dev/test_uninstall.py` skips every version in `KNOWN_BROKEN_TAGS`, imported
   from `tests/kit_dev/test_upgrade.py`. There is one list, never a copy. No other test changes.
2. The authority is the owner's answer on #1258 (Q-1257-2, option (a)).

## Consequences

On main nothing changes that runs. With the 0.64.4 table the test installs 0.64.2 and passes.

## Residual

- None.

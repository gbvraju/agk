# ADR-0539: The upgrade test skips a known-broken tag

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: brief #1273, brief #1257, issue #1256, PR #1258, SPEC-0028 rule 4
- Requirements: REQ-038

Protected classes: `tests/kit_dev/`

## Context

With the corrected file table of release 0.64.4 (#1258), `test_ac1_a_real_old_install_upgrades_with_no_conflict`
reaches the v0.64.3 tag, whose own `init.py` and `adopt.py` refuse to install from its stale table. A release pull
request may change only the release files (SPEC-0028 rule 4), so the test change is this separate build.

## Decision

1. `tests/kit_dev/test_upgrade.py` holds one module-level list, `KNOWN_BROKEN_TAGS = ("0.64.3",)`, with a comment
   naming issue #1256. The test skips each listed version with a reason naming the issue and runs every other version
   as before. No other test changes.
2. The owner's answer on #1258 (Q-1257-2, option (a)) is the authority for this skip.

## Consequences

On main nothing that ran before is skipped (0.64.3 is the current version there). With the 0.64.4 table the two
`0.64.3` cases skip and the rest pass. A later broken tag is added to the one list by a new ADR.

## Residual

- None.

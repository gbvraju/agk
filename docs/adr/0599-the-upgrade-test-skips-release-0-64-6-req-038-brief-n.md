# ADR-0599: The upgrade test skips release 0.64.6

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1431, brief #1424, PR #1429, issue #1424, ADR-0539, ADR-0540, SPEC-0028 rule 4
- Requirements: REQ-038

Protected classes: `tests/kit_dev/`

## Context

Release 0.64.7 (#1429) regenerates the 0.64.6 row of `kit/hashes.json` from release commit 12ed677. Once 0.64.6 is no
longer the current version, the upgrade and uninstall tests install 0.64.6 from 12ed677, whose own `init.py` refuses
from its stale table. A release pull request may change only the release files (SPEC-0028 rule 4), so the test change
is this separate build, as ADR-0539 and ADR-0540 did for 0.64.3.

## Decision

1. `KNOWN_BROKEN_TAGS` in `tests/kit_dev/test_upgrade.py` gains `"0.64.6"`; its comment names issue #1424 beside #1256.
   `tests/kit_dev/test_uninstall.py` already reads that list (ADR-0540) and does not change.
2. The authority is the owner's answer on #1429 (Q-1424-2, option (a)) and the Maintainer answer on #1431 (Q-1431-1).

## Consequences

On main nothing changes that runs, since 0.64.6 is the current version there. On #1429's head the three 0.64.6 cases
skip and the rest of both files pass.

## Residual

- None.

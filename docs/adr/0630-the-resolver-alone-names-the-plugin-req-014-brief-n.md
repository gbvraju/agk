# ADR-0630: The resolver alone names the plugin (REQ-014 AC3)

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1486, issue #1485, SPEC-0071 rule 2, ADR-0611
- Requirements: REQ-014

Protected classes: `tests/kit_dev/`

## Context

The default branch is red since #1469 merged. `test_ac3_no_law_file_depends_on_the_plugin` (REQ-014 AC3) asserts that no
verbatim kit file names `CLAUDE_PLUGIN`, and `scripts/agk/kit_root.py`, the resolver of ADR-0611, names
`CLAUDE_PLUGIN_ROOT` because finding the plugin is its one job (SPEC-0071 rule 2).

## Decision

1. The test leaves out exactly `scripts/agk/kit_root.py`, by name; every other verbatim file is still checked as before.
2. A new assertion: `kit_root.py` is the only verbatim file outside `tests/kit/` that names `CLAUDE_PLUGIN`. A second
   file under the exception fails, and the failure names it.
3. `kit_root.py` is not edited. A test change only; nothing a project runs changes, in any mode.

## Consequences

The default branch turns green. The exception is one named file, guarded by a test of its own.

## Residual

None.

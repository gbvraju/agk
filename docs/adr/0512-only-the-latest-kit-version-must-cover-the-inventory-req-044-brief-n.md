# ADR-0512: Only the latest kit version must cover the inventory

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0037, ADR-0511, brief #1208, plan #661
- Requirements: REQ-044

## Context

`check_design.py` runs `design_prototype_check.version_problems` for every kit version under `docs/design/prototype/`,
and SPEC-0037 rule 7 checks each one against the current `docs/design/inventory.md`. Rule 9 freezes a signed-off
version. When the inventory gains a screen after `v1` is signed off and a later version draws it, `v1` fails rule 7 for
every new state and can never be fixed: in a trial, 19 failing lines on a correct tree.

## Decision

1. `scripts/agk/design_prototype_check.py`: rule 7's coverage (a `yes` state with no page) applies only to the
   highest-numbered kit version. An older version keeps every other check (tokens, colours, contrast, links, runtime,
   accessibility, reflow) and rule 9's frozen digest. A page of an older version for no screen of the inventory fails
   only while that version is not signed off (`design_signoff.signed_off`); the latest version fails it as before.
2. `scripts/agk/check_design.py` prints, for each older version that lacks a page of a `yes` state,
   `design: v<n> predates the inventory; v<m> is the version checked for coverage`, information only; the exit is
   unchanged.
3. SPEC-0037 rule 7 gains one amendment line; `docs/guides/planning.md` one sentence where kit versions are described.

## Consequences

A signed-off version no longer fails forever for screens added after it, and the inventory is still covered by the
version a demo or a build would use. `tests/kit/test_check_design_prototype.py` checks the signed-off `v1` with a `v2`
that covers the new screen (`ok design` and the note), the latest version lacking a state (fails), a single version
(as before, no note), an older complete version (no note), an older page for a removed screen (fails unsigned, passes
signed off) and the frozen digest of an older version (still fails on a change). Protected path classes changed:
`scripts/agk/` (`design_prototype_check.py`, `check_design.py`) and `tests/kit/` (the tests). No workflow changes.

## Residual

- 2026-11-14: an imported version `i<n>` keeps its own coverage rule (rule 15), unchanged; a UI brief's `Screens:` line
  may still name an older signed-off version, which covers only the screens it drew; the maintainers may restrict
  that line to the latest version (due 2026-12-31).

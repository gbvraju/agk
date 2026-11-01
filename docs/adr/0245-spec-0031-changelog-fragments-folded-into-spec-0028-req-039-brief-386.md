# ADR-0245: SPEC-0031 (changelog fragments) folded into SPEC-0028 (the flow-mode release) (REQ-039, brief 386)

- Status: Proposed
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0108, ADR-0188, ADR-0211
- Requirements: REQ-039

Protected classes: `tests/kit/` (`tests/kit/test_core_release_specs.py`)

## Context

SPEC-0031 exists only to change SPEC-0028: its rule 7 amends SPEC-0028 rules 2, 4, 5 and 6, and amendment 54 (ADR-0108)
gave that amendment, but the text of SPEC-0028 still says what it said before it. A reader of the release reads two specs
that edit each other. The core audit (brief #328, `docs/runs/core-audit-2026-10-31.md`) found two verdicts citing SPEC-0028
rule 2 and none citing SPEC-0031. Row 10 of the decision table of the split of plan #278 proposed folding SPEC-0031 into
SPEC-0028; the person accepted it on 2026-11-01 (the field note on #278), with the rule for every merge: never renumber, a
merged number stays as a pointer line. Brief #386 gives five answers.

## Decision

1. **One amendment (answer 1).** `docs/runs/proposed-spec-amendments-108.md` writes SPEC-0028 as it stands with SPEC-0031
   applied: rules 2, 4, 5 and 6 in their amended text (the content of amendment 54, nothing more), and SPEC-0031's rules 1
   to 8, text unchanged, as rules 11 to 18 of a section `### The changelog fragments (from SPEC-0031)` inside `## Rules`,
   where `core_audit.py` counts them. SPEC-0028's Requirements line gains REQ-038 and its `## Tests` one line that points to
   SPEC-0031's tests.
2. **Pointer lines (answer 2).** SPEC-0031 keeps its number, its status and its history, and each of its eight rules
   becomes `N. Now SPEC-0028 rule M.` (M = N + 10). Its `## Tests`, `## Proof`, `## Residual` and `## Open questions` stay
   as they are (Q-386-2).
3. **Nothing else changes (answer 3).** No script, check, workflow, template or kit file changes; `changelog_fragments.py`,
   `check_release.py` and `kit_hashes.py` are not touched, and their docstrings' "SPEC-0031 rule N" resolve through the
   pointer lines. The other amendments of SPEC-0028 (69 and 70) stay in force by their ADRs and are not written into the
   text here (Q-386-3).
4. **No approval (answer 4).** The pull request changes no status line. A person approves SPEC-0028 after the change with
   `Approve: SPEC-0028`; no session posts it.
5. **Tests first (answer 5).** `tests/kit/test_core_release_specs.py` was written first and failed (9 failed, 1 passed)
   before the specs changed.
6. **Protected classes.** `tests/kit/` only. `docs/specs/`, `docs/runs/`, `docs/adr/` and `changelog.d/` are not
   protected path classes. No safety rule is weakened: no check, approval, secret or protected-path rule changes.

## Consequences

The release is read in one spec. A verdict that cites SPEC-0031 rule N is still understood, through the pointer line. The
fold changes the text of an Approved spec, so it waits for a person's approval of SPEC-0028.

## Residual

- 2026-11-01: amendments 69 and 70 of SPEC-0028 are still separate from its text; writing them in is a later brief, if the
  maintainers want it (due 2026-12-31).

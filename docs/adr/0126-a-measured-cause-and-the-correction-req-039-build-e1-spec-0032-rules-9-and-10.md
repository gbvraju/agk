# ADR-0126: a measured cause and the correction (REQ-039 build (e1), SPEC-0032 rules 9 and 10)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0122, ADR-0118, ADR-0110
- Requirements: REQ-039

Protected classes: `.claude/`, `config/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0032 (Approved, #187) rules 9 and 10: the conductor named a cause for a red default branch from reasoning, filed a priority-0 brief on it, and a builder measured another cause; a person had to carry the correction.
This is build (e1) of rule 13 as the conductor split build (e) on #179 (rule 11, the corrections line of the weekly report, is (e2) and waits for the report-schema change). The numbers ADR-0126 and amendment 64 were
reserved on #179. The tests were written first (`tests/kit/test_check_brief.py`, `test_session.py`, `test_session_rules.py`, `tests/kit_dev/test_conductor_role.py`, `test_guide_loop.py`; before the code 7 cases failed).

## Decision

1. **`Measured:`** (`scripts/agk/session.py` `brief_problems`, so `check_brief.py` and `session.py next` apply it): a line `Measured: <command> ... before ... after ...` holds the command run and the output before and after a change
   that turns it green; the check reads that it is not empty and holds the words `before` and `after`, and allows at most one. A hand-written `Priority: 0` brief (now valid beside 1 to 3; `session.py next` orders it before `Priority: 1`, after the router's issue, which alone is handed out and stops other sessions) fails without it, naming rule 9 and
   never the sentence; the brief the router writes for a red default branch (`Advances: none` with `Priority: 0`) needs none because it names no cause. The check cannot tell that the measurement is true: the builder's
   reproduction is the second check.
2. **The builder** (`config/session-rules.md` rule 19): the first step on a brief or fix item that names a cause is to reproduce it with the command of the `Measured:` line; if its own measurement disagrees it posts
   `Question:` with its measurement and builds nothing on that cause.
3. **The correction** (`session.py watch --pr N`): ends with `correction #<n> (comment <id>): <first line>` on a `Correction:` comment by a listed verdict author, newer than the start, on the pull request or on the brief named
   by the `Brief: #<n>` line of its body (the brief is read once at the first poll for its baseline). The session rules name the exception to rule 1 and say in rule 20 that work built on a withdrawn cause is reset with one
   `Report:` and never a force-push. The conductor role file forbids naming a cause without a `Measured:` line and gives the `Correction: <what was wrong>; <what stands>` form for the brief and every pull request built from it.
4. Amendment 64 (`docs/runs/proposed-spec-amendments-64.md`) is applied to SPEC-0034 rule 2, SPEC-0032 rules 9 and 10 and SPEC-0030 rule 2. The guide ("Running the loop") names the correction end. A flow-mode fragment
   `changelog.d/req-039-e1-measured.md` records the change.

## Readings taken where the spec leaves a point open

Recorded as questions in the pull request, the most conservative reading each: `Priority: 0` is allowed for a hand-written brief only with `Measured:`; the shape of the line is the two words `before` and `after`; a
correction is any comment whose first line starts `Correction:` by a listed author (not any comment of a listed author, which would wake a builder on every `taken:` of a shared account); the conductor cannot edit the brief
in place with its guard, so the role file says who does.

## Consequences

- A cause named without a measurement cannot be a priority-0 brief; a builder that measures another cause stops and asks instead of building.
- A builder waiting on `watch` wakes on the conductor's correction on its brief or its pull request, with no person carrying it.

## Residual

- 2026-10-25: the conductor's guard allows only the comment POST, so the conductor cannot edit a brief in place as rule 10 says; a person or the filing session does (due 2026-12-31).
- 2026-10-25: `Measured:` is read for its shape, not its truth, and a fix list that names a cause is not checked mechanically; the role file and the builder's reproduction are the checks (due 2026-12-31).
- 2026-10-25: rule 11, the corrections line of the weekly report, is build (e2) (due 2026-12-31).

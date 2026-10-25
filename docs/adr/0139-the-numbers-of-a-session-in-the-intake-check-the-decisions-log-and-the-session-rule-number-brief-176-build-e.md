# ADR-0139: the numbers of a session in the intake check, the decisions log and the session-rule number (brief #176 build (e), SPEC-0034 rule 4)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0124, ADR-0114
- Requirements: REQ-041

Protected classes: `config/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Three follow-ups were measured on #176 (2026-10-25/26) and gathered by the conductor into build (e), assigned to builder-a: `intake.py check` C1 compares the numbers of an intake with the next free ones of the default branch, so
an intake that took the numbers `session.py ids` printed (skipping those of an open pull request) fails it; C2 allows no file but the requirements file, one spec and one ADR, so the rulings of the intake's questions cannot be
recorded in the decisions log before the spec flips; and two parallel builds that each add a session rule both take the next number and the second to merge conflicts. ADR-0139 and amendment 75 were reserved on #176. The tests
were written first; on the unchanged scripts 12 of the new cases failed.

## Decision

1. **C1 and the numbers of a session.** `intake.py check` and `check --final` take `--ids FILE`, the line `session.py ids` printed; C1 and the file-name checks use its `req`, `spec` and `adr`. Without it the check keeps the numbers
   of the default branch, as before. The check reads the file and makes no network call, so `session.py` stays the only script that calls GitHub; a file that is not that output is refused, naming the option and never its content.
2. **`session.py ids`** also prints `rule`, the next free session-rule number: the highest numbered line of `config/session-rules.md` on the default branch and of the lines that open builder pull requests add to it, plus one.
   `ids --exclude-pr N` leaves the open pull request N out of the count, because the pull request of an intake holds its own numbers: the session runs `session.py ids --exclude-pr <its own> > FILE` and passes `--ids FILE`.
3. **C2 and the decisions log.** `docs/runs/decisions-log.md` may change in an intake when the change only adds lines. A changed or removed row, or any other file, still fails C2.
4. **Session rule 15** gains "a session rule number moved to the next free one (`session.py ids` prints it)" among the mechanical conflicts a session resolves itself, merging and never rebasing.
5. Amendment 75 (`docs/runs/proposed-spec-amendments-75.md`) is applied to SPEC-0034 rules 4 and 7c and SPEC-0012 rule 11. Flow mode: fragment `changelog.d/intake-session-numbers.md`; no version bump.
6. **Readings taken where the build comment leaves a point open** (questions in the pull request, the most conservative reading each): "when it runs in a session" is an explicit option, `--ids`, not a guess from the environment; the
   own pull request and the reservations are read as the caller's own, so only the pull request is excludable by number; the conductor still reserves rule numbers in the `Assign:` comment, since a rule number has no take to
   carry a reservation; the text of the skills that call `intake.py check` is not changed here.

## Consequences

- Two parallel intakes, or two parallel rule additions, no longer take the same number when the sessions use the output of `session.py ids`.
- A session records its question rulings in the decisions log in the same pull request as its intake.

## Residual

- 2026-10-25: nothing makes a session pass `--ids`; the skill text and the rules file say nothing of it yet, so an intake checked without it keeps the default-branch numbers (due 2026-12-31).
- 2026-10-25: a reservation by the session's own take is counted in the numbers it prints, since only a pull request can be excluded (due 2026-12-31).

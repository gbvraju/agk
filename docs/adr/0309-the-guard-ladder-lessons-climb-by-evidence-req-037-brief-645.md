# ADR-0309: The guard ladder: a lesson climbs to a rule, a test, a check or a workflow by evidence (REQ-037, brief 645)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0294, SPEC-0004
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`, `kit/`

## Context

The owner directed on 2026-11-06 (conductor chat, quoted as data in brief #645) that AGK know what a lesson, a rule or a
workflow is: a lesson is first a log line that may or may not be followed, and later it becomes a rule. The conductor catch
log of ADR-0294 carries a Guard column (`check`, `test`, `rule`, `pending`) and the role file says each `rule` row is
"revisited monthly", but nothing names the levels as one ladder, decides when a row is due to climb or keeps the record
checkable outside the kit's own test of that log.

## Decision

1. **One ladder**, weakest first: `lesson` (no guard yet; written `lesson`, `pending #n` or `pending (to be filed)`), `rule`
   (a line of an agent or guide file that cites the row as `(row N)`), `test`, `check`, `workflow` (CI or a scheduled job
   enforces it; on the owner's hold list). Each guard after `lesson` is written `` <level> `<path>` `` with an optional note
   in parentheses; several guards are separated by `; `. A row's level is the strongest it holds. The ladder is written in
   `docs/guides/guard-ladder.md` and in the docstring of `scripts/agk/lessons.py`, which a project installs.
2. **Promotion rules, decided from the logs alone.** A `lesson` row is due to become a `rule` when another row has the same
   kind and the same cause (compared without case, spacing or a final period), or when its cost is one hour or more (`N h`
   or `N min`; an unknown cost never is). A `rule` row is due to become a `test` or a `check` when a row of the same kind and
   cause is dated after it, or when 30 days have passed since its date. The date of a `rule` row stands for the day its rule
   line was added, because the conductor logs the row and its line in one change (ADR-0294 decision 3). A `test` or a `check`
   row is never due: a check becomes a workflow only with the owner's yes. A due row is never promoted by the command: it is
   listed, and the conductor files the brief.
3. **`lessons.py ladder`**, read-only and GET-free, reads `docs/runs/*-catches-*.md` under `--root` (the current folder by
   default) and the files the guards name, and prints every row with its level, every row due to climb with the rule it
   meets, every `rule` guard whose file has no line citing the row, every guard whose file is missing, every malformed
   guard, every row the date rules cannot decide, and every log without a Guard column (not on the ladder), then one count
   line. It exits 1 on a malformed guard or a missing line or file, 0 otherwise: the due list never blocks. Usage errors
   exit 2 naming the option, never a value.
4. **A kit test** (`tests/kit/test_lessons.py`) tests the command on invented logs and runs it on this repository's own
   logs, so a malformed guard or a missing rule line fails the kit's suite.
5. **The weekly pass is a follow-up.** The drift audit (SPEC-0004, Approved) has no listed, non-blocking kind of finding: a
   finding of it opens or updates the audit issue (rules 11, 13 and 14), so carrying the due list there changes the spec.
   This build writes no amendment; the command is this build, and the weekly wiring is a later brief with amendment 125
   and the owner's `Approve: SPEC-0004`.

## Consequences

A lesson's climb is decided from the record and listed by one command, in this repository and in a project with its own
catch logs. The architect catch logs have no Guard column and are named as not on the ladder until a later change gives them
one.

## Residual

- 2026-11-06: the weekly pass is not wired; the due list is read only when a person or the conductor runs the command
  (due 2026-12-31).
- 2026-11-06: the kit-only test of the conductor catch log (ADR-0294) accepts four guard forms; a row written `lesson` or
  `workflow` passes `lessons.py` but fails that test until it is widened (due 2026-12-31).

# ADR-0308: The conductor's routines become kit commands (REQ-037, brief 643)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0294, ADR-0265, ADR-0297, ADR-0302, SPEC-0039
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `.claude/`, `agk.toml`, `kit/`

## Context

Rows 1, 2, 3, 12 and 13 of the conductor catch log (`docs/runs/conductor-catches-1.md`) are rule
lines of `.claude/agents/conductor.md`; each cost 1.5 to 7 hours. This repository's conductor runs
its watch, its sweep and its merges as shell scripts outside the kit, so another project's
conductor would have to write them again. Brief #643 (tracker #630 item 9, the owner's yes of
2026-11-06) makes them kit commands in two builds; this ADR is written by build (a) and covers both.

## Decision

1. **`scripts/agk/conductor.py`, read-only (build (a)).** It reads GitHub with GET only, posts
   nothing and writes no file. `watch [--since ISO] [--once]` polls the comments of every open
   issue labelled `agk-brief` (the router's red-branch issue carries that label) and every open
   pull request, and exits 0 printing `<number> <first line>` for each comment created after
   `--since` (default: the start) whose first line starts `Question:` or `Report:`; `--once`
   reads once and prints `nothing new` when there is none. A read that fails is printed
   (`error: ... cannot be read; retrying`) and retried. `sweep` prints `#<n> <head7> <state>
   <age>` per open pull request, its state one of `draft`, `ready: no verdict`, `fix list on
   <head7>`, `cleared on <head7>`, `cleared, head moved`, `waiting: Approve SPEC-nnnn at <head7>`,
   `blocked: Question Q-n unanswered <age>`, `checks pending` and `red`, then the latest run of the
   default branch and each open red-branch issue. A `Question:` or `Report:` with no comment by a
   listed verdict author after it, older than the threshold, is marked `LATE`.
2. **Settings.** `conductor_poll_seconds` (60 by default) and `conductor_late_minutes` (30 by
   default) of the `[flow]` table of agk.toml, each a whole number, 1 or more. This repository sets
   neither.
3. **No rule copied.** The checks state is `session.check_state` (the router's reading); the
   verdict is `session.last_verdict` over `counted_authors`; the spec approval is
   `merge_cleared.unapproved` with `reviewers.approval_shas`, without the local git reads of
   amendment 124, so a sweep may show `waiting: Approve` where the merge would count an approval of
   an unchanged earlier text; the red-branch issue is `session.is_red`.
4. **The guard.** `.claude/hooks/conductor_guard.py` allows exactly `python3
   scripts/agk/conductor.py sweep` and `... watch`, with `--since <YYYY-MM-DDTHH:MM:SSZ>`, then
   `--once`, or both in that order, the project's own regular file; every other form, such as
   `merge-queue`, stays denied.
5. **The lessons.** The lesson lines of rows 1, 12 and 13 name the commands, and the log's Guard
   column for those rows gains `check scripts/agk/conductor.py` before the rule line, which stays.
   Row 2 stays a rule line.
6. **Build (b), `merge-queue [--dry-run]`.** It runs `merge_cleared.py --pr N --sha <head>` for
   each cleared pull request in the order of the verdicts and stops at the first `held` or
   `stopped` line, as the brief states it; its build adds its guard form and the row 3 line. It is
   not built here.

## Consequences

A conductor of any project gets the watch that missed a brief's question (row 1) and the sweep that
shows a late report (row 13) from the kit, and its guard lets it run them. The sweep reads, per open
pull request, its comments and, unless it is a draft or blocked, its check runs and statuses: two to
four GETs each.

## Residual

- 2026-11-06: build (b) (`merge-queue`) is the brief's follow-up on the same brief.
- 2026-11-06: Q-643-1, whether `watch` should also end on `Progress:` lines (the brief's line
  format names it; its trigger list does not). Read as not, the conservative reading.

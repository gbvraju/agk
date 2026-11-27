# ADR-0852: Every shipped decision names a signal of use, and the weekly report lists the unused

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2054, 2026-11-27T19:12:17Z)
- Related: ADR-0016, ADR-0374, ADR-0188, ADR-0560, ADR-0752, ADR-0835, ADR-0348, ADR-0417, ADR-0586, SPEC-0007, REQ-012, brief #2054, brief #2012, brief #1163, plan #661
- Requirements: REQ-012

Protected classes: `config/`, `scripts/agk/`, `tests/kit/`, `agk.toml`, `docs/guides/reference.md`

## Context

Test selection, the conductor's light re-prove, short builder jobs and the merge queue were built and wired, and found
unused, defeated or blocked only when the owner asked for a check of the code. Nothing in the kit says that a built
feature is not used. An Accepted ADR changes only its Status line and a brief is an issue, so the one tracked, reviewed
and offline place for the declaration is a registry under `config/`, a protected class. `metrics.report` already builds
the weekly body that the `metrics` workflow posts, and the steward's `Daily:` list already reads the issues changed
since the first day it lists.

## Decision

1. **The registry.** `config/signals.toml` holds `from` and one `[[signal]]` per shipped feature: `id`, `feature`
   (`ADR-nnnn` or `brief #n`), `since`, `kind` (`log`, `comment`, `run`, `commit` or `none`) and its fields, and an
   optional `setting` (`<table>.<key>` of `config.TABLE_KEYS`, or a top-level key). Patterns are regular expressions
   of at most 200 characters, matched per line. `metrics.signal_lines` is its only reader. Six rows are seeded:
   `tests-selected`, `light-reprove`, `short-jobs`, `usage-figure`, `merge-queue` and `unused-on-owner-list`.
2. **The reading.** For the 14 days ending the report's window end: `log` reads the newest five governance
   `pull_request` runs, their jobs and the named step's log; `comment` reads one paged `issues/comments?since=` (with
   `then`, only a match followed on the same issue by a later match of `then`); `run` reads `total_count` of the
   event's runs; `commit` reads `git log --first-parent origin/<default_branch>` offline. Every read is metered by
   `min(hourly_room, 20)`; `GET rate_limit` is not counted.
3. **The lines.** After the stale pack lines: `signals: <n> declared; used <a>; unused <b>; new <c>; unknown <d>
   (14 days to <end>)`, one `unused:` line per unused row (ending `; off by <setting>` when that setting is false or
   absent), one `unknown:` line per row with a read not answered, and the decisions dated on or after `from` that no
   row names. A row whose `since` is in the window or later is `new`; a `none` row is counted as `no runtime use`. A
   zero is printed only when every read the row needs was answered. `metrics.py --signals` prints the section alone
   and writes nothing; `--saved FILE` serves the comment and run rows from a saved checklist, which now records its
   `days`.
4. **Settings.** No registry: `signals: none declared (path class: config/)`. A broken registry: `signals: refused
   (field: <field>)`, never a value, the rest of the report unchanged. `execution = "local"`: log and run rows
   `unknown (setting: execution)`. A `[personal]` table: commit rows only, the rest `unknown (setting: forge)`. The
   section adds no failure: `report` returns `incomplete` only for its own records.
5. **The owner's list.** `steward_daily.daily_text` adds `Built but unused: <id> (<feature>)` per `unused:` line of the
   newest weekly metrics issue among the issues it already reads (of its week, the lowest number), else `Built but
   unused: none (agk metrics <week>)`, or `Built but unused: unknown`; no new call.
6. **New briefs.** `brief_study.signal_problems` warns when a brief's `Measured:` after-part names no `signal: <id>`
   or `signal: none (<reason>)`; it never fails.

## Consequences

A feature that real runs never use is named every week and reaches the owner's Daily list. Each later build that ships
a feature adds its row to `config/signals.toml` with its own ADR; a decision dated on or after `from` without a row is
shown every week until its row lands. The weekly cost is at most 20 GETs inside the existing metrics job. No workflow,
ruleset, required check, label, `agk.mk` or `governance_map.CHECKS` changes. `init` and `adopt` install no registry
(`Q-P0C-4`), so `config/signals.toml` is one line of `config/kit-only.txt`, and the ceiling of that list in
`tests/kit/test_parity.py` rises from 11 to 12 by this decision, as ADR-0627 and ADR-0846 raised it.

## Residual

The `short-jobs` row pairs a supervisor's `Started:` with a later `Report:` on the same issue; a build job's claim is
posted on its brief and its `Report:` on the pull request, so only fix jobs pair until a later brief reads the pull
request that names the brief (`Q-2054-1`).

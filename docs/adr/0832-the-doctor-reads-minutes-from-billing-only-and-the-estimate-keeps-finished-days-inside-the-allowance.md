# ADR-0832: The doctor reads the minutes from billing only; the estimate keeps finished days and stays inside the allowance

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's yes on brief #2011, 2026-11-26T17:56Z)
- Related: ADR-0215, ADR-0476, ADR-0184, brief #2011, plan #661
- Requirements: REQ-020

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`, `skills/`

## Context

The conductor's doctor run on main took about 1 hour 40 minutes on 2026-11-26, almost all of it in the `actions-minutes`
check: the token cannot read billing, so `minutes.outlook` fell back to `minutes.estimate` (ADR-0215), which lists every run
of the month by windows (ADR-0476) and reads one job list per run, about 40,000 GET calls. Half of the newest runs were
`skipped` and cost nothing, a finished day's runs never change, and the account's hourly REST allowance of 15,000 calls,
shared by every session, ran out twice that day.

## Decision

1. `minutes.outlook` (the doctor's `actions-minutes` and `minutes.py --line`) reads billing only and never estimates. When
   billing cannot be read the line is `actions minutes: unknown (the token cannot read billing: <reason class>); run python3
   scripts/agk/minutes.py for the estimate`, and the doctor's check is `cannot-check` with the reason `minutes-unknown`,
   whose hint names `minutes.py`. This replaces ADR-0215's estimate in the doctor's line (`Q-DM-2`); the line with billing,
   and its levels, are unchanged.
2. `minutes.estimate` reads no job list for a run whose `conclusion` is `skipped`, and counts it in `skipped_runs`. Every other
   run, `cancelled` included, is read (`Q-DM-4`).
3. `minutes.estimate` keeps each finished UTC day's sums, per day the runs were created, as one JSON file per day in
   `<git common dir>/agk-minutes/<owner>-<repo>/<YYYY-MM-DD>.json` (schema 1: the run ids, the skipped count, and per day
   the jobs started the minutes per workflow after the runner rates, the self-hosted and the running job counts, and the rates
   they were counted with). A day is written only when it is before today, its run list was not capped, every run on it was
   read, every job list answered 200 and no job was still running, whole by rename. A later reading takes a kept day from its
   file and lists and reads only the days without one and today. A file that cannot be parsed, of another schema or of the
   other rates is ignored and the day read again. A source keeps days only through its `keep` folder: `minutes.Gh` finds the
   git common dir, `minutes.ApiDir` (`--api-dir`) keeps none unless a test names a folder, and any other source keeps none.
   Days are kept and read only when every bound of the window is a UTC midnight.
4. Before reading job lists, `minutes.estimate` reads `/rate_limit` once (verify: GitHub does not count it against the
   allowance) and reads at most `remaining` less `ALLOWANCE_MARGIN` (2,000) job lists, oldest day first, so the days it
   finishes are kept. When `/rate_limit` cannot be read, or the source cannot read it, it reads at most `UNREAD_LIMIT` (1,000).
   A reading stopped early is not complete and the report says `actions minutes: at least <n> used this month (<k> of <m> days
   read; run again after the GitHub allowance resets at <HH:MM UTC>)`, or `resets, at a time that cannot be read`. The two
   numbers are named constants, not settings (`Q-DM-1`).
5. ADR-0476's windows are kept; the run list is now asked once per run of consecutive days without a kept file.

## Consequences

The doctor's check makes at most two GitHub calls (the repository read it shares, and billing) and ends in under a second; a
repeated report reads only today and the days not yet kept, and leaves 2,000 calls of the hourly allowance to the other
sessions. Every caller of `minutes.estimate` (`minutes.py`, `measures.py`, `facts.py`, `scorecard.py`) gets the skip and the
allowance; the callers that answer from their own reads keep no day. No workflow, label, check or ruleset changes.

## Residual

- 2026-11-26: whether `/rate_limit` is free of the allowance is marked (verify).

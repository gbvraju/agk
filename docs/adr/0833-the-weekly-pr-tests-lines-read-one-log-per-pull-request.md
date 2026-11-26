# ADR-0833: The weekly `pr tests` lines read one log per pull request

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's yes on brief #2012, 2026-11-26T18:12Z)
- Related: ADR-0359, ADR-0393, ADR-0422, ADR-0440, ADR-0692, REQ-062, brief #2012, plan #661
- Requirements: REQ-062

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

ADR-0359 rule 5 and ADR-0393 rule 5 rely on the weekly report's `pr tests:` lines: the share of pull requests that ran
only their selected tests, the minutes of each mode and the reason of each full run. The lines have never measured it:
2026-W45 (#907) read `unknown: 99`, W46 (#1427) `unknown: 372` and W47 (#1871) `unknown: 247`, with `0 runs`. The section
read the commits of every pull request, the runs of every commit, the jobs of every governance run and a log per run:
several thousand REST calls a week with the workflow token, after the other sections had read theirs. A read that
failed became `unknown` with no reason said. A full run for `[testing] full_when_share` (ADR-0422 rule 3, reason
`selection <n> of <m> files`) was counted as `other`.

## Decision

1. **One log per pull request** (`scripts/agk/metrics.py`, `pr_tests_lines`, `pull_tests`, `tested_run`). For each pull
   request of the week the section reads the runs of its last head, keeps the latest governance run of event
   `pull_request` whose test step ran (`pr_test_step`, as before; a `governance edited` run is passed over unread), and
   reads that run's jobs and one job log. Only when the last head has no such run does it read the commits and take the
   latest earlier head that has one. The counts are per pull request: `pr tests: <n> pull requests; selected <k> of <n>
   (<share>); ...`, and the median line counts pull requests.
2. **The `share` kind** (`full_kind`, `FULL_KINDS`). A reason that starts `selection ` is `share`; `FULL_KINDS` is
   `always_full, unmapped, share, thorough, other`, and `pr tests full reasons:` names it `share`.
3. **Why a read failed** (`Gh.raw`, `Gh.why`, `ApiDir.why`). A failed read keeps its class: `rate-limited` for a 403 or
   429 that GitHub says is a rate limit, `refused` for another 4xx, `failed` otherwise. A recorded answer in
   `--api-dir` whose body holds only `message`, `status` and `documentation_url` is a failed read of that class. The
   line ends `unknown: <n> (<class> <count>, ...)`; a log with no mode line is `no mode`, a step that has not ended is
   `not ended`, and, with `execution = "local"`, a pull request with no governance run that ran tests is `no CI run`.
   Before the section `metrics.py` reads `GET rate_limit` once (GitHub does not count it, as `session.py` reads it);
   when `resources.core.remaining` is below four calls per pull request (runs, jobs, the log and a commits page), it
   reads the newest pull requests that fit and adds the line `pr tests: <k> of <n> pull requests read (hourly limit)`.
   An unreadable or unrecorded answer reads as unlimited.
4. **What does not change.** No selection rule: ADR-0359, ADR-0393, ADR-0422, ADR-0440 and ADR-0692 stand. No workflow
   file. `checklist.py` reads the `pr tests:` line in both the old `<n> runs` and the new `<n> pull requests` form, so a
   saved weekly issue of an earlier week still reads.

## Consequences

The section's reads fall to about three per pull request, so the weekly workflow can finish inside the workflow token's
hourly limit, and a refused read says why. The weekly figures count pull requests, not runs, so they are not comparable
with a run count of an earlier week. The ADR-0359 rule 5 and ADR-0393 rule 5 lines become readable without changing what
they report.

## Residual

None.

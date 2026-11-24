# ADR-0776: Each GitHub job records the calls it made and the hourly limit left (REQ-039)

- Status: Accepted
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1877, ADR-0529, ADR-0548, ADR-0565, ADR-0566, ADR-0654, ADR-0653, ADR-0196, plan #661
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

On 2026-11-23 three governance runs of #1870 failed only on GitHub's hourly limit, shared by every job that reads with
the workflow's own token, and no run said which jobs spent it. `session.gh` already counts its calls (`CALLS`), cached
answers (`CACHED`) and writes (`WRITES`), and reads the `x-ratelimit-*` headers of each headed read, but nothing writes
them out in a job, and the router's writes and searches and the merger's direct `gh api` calls bypass the counter. The
owner's word (the steward chat, 2026-11-24, quoted as data): "Yes, draft all four along with release", then "Yes".

## Decision

1. `session.call_record()`, registered with `atexit` beside the read cache's save, runs only when `GITHUB_ACTIONS` is
   `true` and the process made at least one call. It prints to standard error and appends to `$GITHUB_STEP_SUMMARY`,
   when set, one line: `github calls: <workflow> / <job>: <n> calls (<c> cached, <w> writes, <k> waits, <s> s waited);
   limit <r> of <l> left, resets <HH:MM>Z`, from `GITHUB_WORKFLOW` and `GITHUB_JOB`. The limit figures are the last
   `x-ratelimit-*` headers a call of the process saw; with none, one `GET rate_limit` (`rate_state(limit=True)`, free and
   not counted); a figure that cannot be read is `unknown`, never 0. The line names counts and times only, never an
   endpoint, a token or a body.
2. A summary that cannot be written prints `github calls: the job summary cannot be written (setting:
   GITHUB_STEP_SUMMARY)` once; the exit code never changes. A killed process writes nothing.
3. `session.count_call(method)` counts a call made outside `gh`: `route.write`, `route.search_once` and
   `merge_cleared.gh_api` when called directly (not through `shared_get`, which `session.gh` counts). `gh` adds each
   limit it waits out to `WAITS` and its seconds to `WAITED`. `session.py plan`'s `reads:` line is unchanged.
4. Governance's reads stay in the workflow file and are not counted; no workflow, check, label or status changes
   (`Q-API-1`). A rate-limited governance step stays red (principle 11; `Q-API-2`). No metrics record changes
   (`Q-API-3`). The GITHUB_TOKEN hourly figure and whether a cloud session's calls share the workflows' bucket stay
   unconfirmed (verify); the line prints what GitHub's headers say (`Q-API-4`).
5. Path classes changed: `scripts/agk/` (`session.py`, `route.py`, `merge_cleared.py`), `tests/kit/`
   (`test_github_call_record.py`; `conftest.py` drops the runner's `GITHUB_ACTIONS` for kit tests, so a test's `gh`
   double never sees the record; a test that needs it sets it) and `agk.toml` (the new test joins the three scripts' map entries). `kit/` is named
   for the installed scripts' hash rows, which the release regenerates (session rule 14); this build leaves
   `kit/hashes.json` unchanged.

## Consequences

Each router and merger job that calls GitHub shows its spend and the limit left in its summary and log, so the next
brief cuts the biggest spenders by measured figures. Outside Actions (local, pool, personal mode) nothing is printed.

## Residual

Counting or wrapping governance's own reads (`Q-API-1`) and a `not run: rate limit` wording with one retry (`Q-API-2`)
are for the next brief, under its own ADR (from 2026-11-24).

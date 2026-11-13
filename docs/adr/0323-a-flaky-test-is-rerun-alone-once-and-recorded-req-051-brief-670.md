# ADR-0323: A flaky test is rerun alone once and recorded, never hidden (REQ-051, brief 670)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0234, ADR-0270, ADR-0303, SPEC-0044, SPEC-0046
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

Tracker #630 decision 2 (brief #670): a test that fails in the full suite and passes when rerun
alone fails the whole run today, and nothing records it, so the next run repeats the cost and the
flake has no owner. SPEC-0044 rule 1 says no rule retries away or quarantines a test. This decision
changes that only as far as one isolated rerun that is always recorded; the spec text changes only
through proposed amendment 135 (`docs/runs/proposed-spec-amendments-135.md`), which the owner
decides. The tests were written first (`tests/kit/test_rerun_alone.py`: 15 failed, 4 passed).

## Decision

1. **Off by default (answer 1).** `[testing] rerun_alone` is `true` or `false`, `false` without
   the table or the key; another value is refused naming `testing.rerun_alone`. With it absent or
   false every command prints and runs what it does today. `project_tests.py --no-rerun-alone`
   turns it off for one call; `--rerun-alone` without the setting is refused naming it.
2. **The rerun (answer 1).** When the full run fails, `project_tests.py` reads the failed test ids
   as `failures.py signature` does (the JUnit report at `[testing] junit`, else `FAILED <id>`) and
   reruns each alone, once, at the top of the repository: the project's pytest command up to
   `pytest`, its `-c`, `-p`, `-o`, `--rootdir` and `--confcutdir` options, then the test id. A
   command that is not pytest, a run with no test id and a run with more than ten failed tests are
   not rerun: one line, and today's exit code.
3. **The strike (answer 2).** A pass alone is one strike written by `flakes.py add` (new): a new row
   is `watch`, one strike, the owner `AGK_SESSION` or `unassigned`, an expiry 30 days from the UTC
   date; an existing row gains a strike and keeps its owner, status and expiry. The run prints the
   failure signature of SPEC-0046 and the action of `failures.py issue-body` (`action: none` while
   `[failures] issues` is off). It posts nothing: checks make no network call.
4. **The exit (answers 1 and 3).** The run exits 0 only when every failed test passed alone; a test
   that fails alone is a real failure and the run keeps today's non-zero code.
5. **The expiry (answer 2).** `flakes.py` (and its new spelling `flakes.py check`) lists as
   `expired` any entry whose expiry is before today, a watched strike as well as a quarantine
   (`watched until <date>`), so an entry past its expiry fails the check until a fix removes the
   row. This widens ADR-0234 decision 2, which listed only quarantines; a quarantine's line and
   JSON entry are unchanged.

## Consequences

A flake no longer turns a whole run red, but it can never pass silently: every rerun pass is a
strike with an owner and an end date, two strikes are a brief due, and an expired entry fails
`flakes.py`. Projects that do not set the key see no change.

## Residual

- Q-670-1 (2026-11-06): "an expired entry without a fix" is read as a row still in the ledger past
  its expiry; the ledger has no fix column, so a fix removes the row.
- Q-670-2 (2026-11-06): the brief does not say how one test is run alone; read as pytest only, with
  the listed options kept, and nothing for other runners.
- Q-670-3 (2026-11-06): the strike is written to the run's working tree; in CI it is not committed,
  and recording it on the default branch stays a pull request of its own (ADR-0234 decision 3).
- Q-670-4 (2026-11-06): "opens or updates its failure issue" is read as printing the signature and
  the issue action, since checks make no network call; the posting stays with SPEC-0046's wiring.

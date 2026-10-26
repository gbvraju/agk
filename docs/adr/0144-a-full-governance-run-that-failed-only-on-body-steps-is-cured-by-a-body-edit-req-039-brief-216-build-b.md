# ADR-0144: a full governance run that failed only on body steps is cured by a body edit (REQ-039, brief #216 build b)

- Status: Proposed
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0137, ADR-0143
- Requirements: REQ-039

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`

## Context

Build (a) of brief #216 (ADR-0137) lets an edited description start a partial `governance` run, and its first step (`full_run.py`) fails unless the latest full run of the head succeeded, so that a partial run cannot turn a failed full run green. Found on #227 (Q-227-1) and recorded on #216 on 2026-10-26: a full run that fails only on the steps that read the body (for example a `Build-state row:` without a date) cannot be cured by editing the body: the partial run then fails with "the latest full governance run of the head did not succeed", a re-run replays the old body, and only a new push clears it. The conductor made the follow-up build (b) of the brief and assigned it to `builder-b` on #216 with this ADR number and amendment 80 reserved. The tests were written first (`tests/kit/test_full_run_body_steps.py`: 28 failed and 8 passed on the unchanged tree).

## Decision

1. **`full_run.py`** (`scripts/agk/full_run.py`) gains the option `--jobs FILE`. When the latest full run of the head is red and no jobs file is given it prints `jobs <run id>` (digits only; any other value fails) and exits 4. With `--jobs FILE`, the saved response of `GET actions/runs/<id>/jobs`, the red run passes when its conclusion is `failure`, it has at least one failed step, and every failed step has the conclusion `failure` and is a body step. Any other failed step, a cancelled or timed-out step, no failed step (an infrastructure failure), a run that was cancelled and an unreadable response fail. A green run and a running run are decided as before.
2. **The body steps** are the steps of `governance.yml` that run on an edit and read the body: `PR body file`, `PR states and open pull requests`, `check_specs`, `check_pr_mode` and `PR body shape`. A test pins the constant `BODY_STEPS` to the workflow, so that a step added or renamed there fails the test instead of silently curing or blocking (Q-K4-319).
3. **The workflow** (`.github/workflows/governance.yml`, step `Latest full run`): on exit 4 it makes one more `GET` of `actions/runs/<id>/jobs?per_page=100` and calls the script again with `--jobs`. The job stays read-only (`actions: read`). The step is the only place that makes the GET; the script reads files only. The maintainer merges this pull request, because it changes `.github/`.
4. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-sj.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. Amendment 80 (`docs/runs/proposed-spec-amendments-80.md`) is for SPEC-0007 rule 13.

## Consequences

- A pull request whose full governance run failed only on its body can be fixed by editing the body, with no new push; the partial run repeats those steps and decides.
- Any failure in code, lint, tests or another check still needs a new push, as before.

## Residual

- 2026-10-26: a body-step failure and another failure in different runs of one head are decided by the latest full run alone; the partial run does not know the earlier ones (due 2026-12-31).

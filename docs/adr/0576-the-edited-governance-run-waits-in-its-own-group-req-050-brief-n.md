# ADR-0576: The edited governance run waits in its own group

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: ADR-0480, ADR-0302, ADR-0505, brief #1371, found bug #1253, brief #1122, brief #216, brief #621, plan #661
- Requirements: REQ-050

Protected classes: `.github/`, `tests/kit/`, `kit/`

## Context

Found bug #1253 was seen four times on 2026-11-14 and 2026-11-15 (#1249, #1271, #1286, #1352). A builder pushes, then
within about three seconds edits the body (`edited`) and marks the pull request ready (`ready_for_review`), the order its
prompt asks for. Both `governance full` runs of the head ended cancelled with no step run, and the `governance edited`
run failed with `FAIL full-run: rule 2: the latest full governance run of the head did not succeed`, so the router
labelled the pull request `agk:ci-red` with no check failing.

ADR-0480 decision 1 put the edited run in the full runs' group, `governance-<n>-code`, with `cancel-in-progress` false
for it and true for the full runs. GitHub keeps one running and one pending run per group, and a newer pending run
replaces an older pending one whatever `cancel-in-progress` says (verify: GitHub's concurrency documentation). So the
`ready_for_review` full run cancelled the running `synchronize` run and waited as the pending run, then the `edited` run
replaced it, and no full run of the head was left. The edited run already orders itself after the full run without
the group: its step `Latest full run` reads the head's latest full run every 30 seconds, for at most 20 minutes, and
fails closed (ADR-0480 decision 2).

## Decision

1. **The edited run has a group of its own.** In `.github/workflows/governance.yml` a pull request run for an edited
   description is in `governance-<n>-edited`; every other pull request run stays in `governance-<n>-code`; a push to the
   default branch keeps its fixed batch group `governance-<branch>-code` (ADR-0302); a merge queue commit keeps its own.
   `cancel-in-progress` is true for every pull request run: among full runs as before, and among edited runs, where a
   newer edit cancels a superseded edited run. An edited run can never cancel or replace a full run. This replaces
   ADR-0480 decision 1; its decisions 2 to 4 stand.
2. **The order between them** is the step `Latest full run` alone. An edited run that starts while the full run is
   queued or in progress holds a runner while it polls, as before brief #1122: that cost is taken in exchange for never
   losing the head's full run.
3. **`proof.yml` is unchanged.** It runs on no `edited` event, so every run in a pull request's `proof-<n>` group is a
   full run of that pull request, and a replacement there is always by a newer full run.
4. **A test pins it without GitHub.** `tests/kit/test_workflow_concurrency.py` evaluates each workflow's `concurrency:`
   expressions for invented events (a small evaluator of the expression subset the two blocks use) and asserts that no
   `edited` run shares a group with a `pull_request` full run, that every pull request type of the governance workflow
   is covered, that the default branch's push group and its cancel rule are unchanged, and that the proof group holds
   only full runs. The text tests of ADR-0480 in `test_workflow.py`, `test_main_batching.py` and `test_ci_saving.py`
   change to the new group.
5. **The workflow file is the owner's** (ADR-0505): the builder commits the whole proposed file at
   `.agk/workflow-proposals/governance.yml` and the owner applies it with `/agk:workflow-apply <pr>`. The builder
   prompt keeps its order (push, body edit, ready); the workaround of editing the body before the push is not needed.

Protected path classes changed: `.github/` (`.github/workflows/governance.yml`, applied by the owner), `tests/kit/`
(`test_workflow_concurrency.py`, `test_workflow.py`, `test_main_batching.py`, `test_ci_saving.py`) and `kit/`
(`kit/hashes.json` only as `kit_hashes.py` writes it).

## Consequences

A push followed at once by a body edit and ready-for-review keeps a full governance run of the head, so the edited run
reads a real result and the router no longer labels a pull request `agk:ci-red` with no check failing. An edited run
that starts during a full run again holds a runner while it polls, for at most 20 minutes, which gives back part of
the minutes ADR-0480 saved.

## Residual

- 2026-11-15: the replacement rule of a pending run is GitHub's (verify); the next push, body edit and ready within
  seconds after the merge is to show one `governance full` run that ran its steps (due 2026-12-31).
- 2026-11-15: the minutes an edited run spends polling are to be read from the step timings of a comparable day after
  the merge (due 2026-12-31).

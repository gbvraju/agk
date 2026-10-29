# ADR-0174: the router never drops a wake when events arrive together (REQ-039, brief 309)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0165
- Requirements: REQ-039

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #309 (priority 1). The router workflow (`.github/workflows/agk-route.yml`) used one concurrency group, `agk-route`, for every
event. GitHub keeps one pending run per group and cancels the older pending run when a newer one queues, even with
`cancel-in-progress: false`. Reproduced by the builder from the runs of the router in this repository on 2026-10-29
(`gh api 'repos/gbvraju/agk/actions/workflows/agk-route.yml/runs?created=2026-10-29T21:10:00Z..2026-10-29T21:20:00Z'`): the two
`workflow_run` runs of 21:13:54 and 21:13:56 ended `cancelled`, next to `pull_request` runs of another pull request's branch at
21:13:54 and 21:14:02. The tests were written first (`tests/kit/test_route_wakes.py`,
`tests/kit_dev/test_route_concurrency_install.py`, 7 failed at the first checkpoint of the pull request, 16cbe5f).

## Decision

1. **A group per pull request** (answer 1): `agk-route-${{ github.event.pull_request.number || github.event.issue.number ||
   github.event.workflow_run.pull_requests[0].number || github.event.workflow_run.head_sha || github.ref }}`, with
   `cancel-in-progress: false`. All the events of one pull request share its number's group (verdict on 5a9fb92, item 1):
   `pull_request`, `issue_comment` and a `workflow_run` through the run's pull request, so two runs of one pull request never
   write its label at the same time. A `workflow_run` with no pull request (a fork's run, a run on the default branch) falls back
   to its head, and a push to its branch. Events of different pull requests never share a group; events of one pull request may
   still replace each other, because the latest run reads the latest state.
2. **The sweep** (answer 2): a run woken by `workflow_run` (not `--pr`, `--all` or `--branch`) also reads the open pull requests and,
   for each one labelled `agk:ci-running` that the event did not name, reads its facts and applies `decide`; it writes the label
   when the result is another label, and nothing while the result is still `agk:ci-running`. It writes labels only: no correction
   comment, unlike `route_one`. An unreadable list or pull request fails the run naming the rule, after the named pull requests
   were routed.
3. **Installs** (answer 3): `init.py` and `upgrade.py` already write the kit's router with only its `workflows:` line set from the
   project (brief #285, ADR-0165), so they install the new group and keep the project's names with no code change; tests show it
   for both, including an upgrade of a released copy with the single group and hand-added names.
4. **Tests** (answer 4): two pull requests whose checks finish together both leave `agk:ci-running`; the sweep relabels a stale
   one, leaves a running one and one under another label alone, writes only labels, and runs only on `workflow_run`; the workflow
   has the per-pull-request group; the existing tests that the router checks out the default branch and runs no code of a pull
   request still pass.
5. **Numbers and mode.** Q-309-1, answered (verdict on 5a9fb92): ADR-0174 is confirmed, reserved by the conductor in a field
   note on #309. Flow
   mode: fragment `changelog.d/router-wakes.md`; no version bump; `kit/hashes.json` is not edited (session rule 14). The install
   tests are in `tests/kit_dev/`, outside the brief's `Touches:`, because `init.py` and `upgrade.py` are not vendored.

## Consequences

- A wake of one pull request is never cancelled by another pull request's event, and a lost wake is repaired by the next finished
  workflow of any pull request.
- A run woken by a finished workflow reads every open pull request once more, and the facts of each one left at `agk:ci-running`.

## Residual

- 2026-10-29: the sweep runs only when some workflow finishes; a lost wake with no later finished workflow in the repository still
  waits for the next event (due 2026-12-15).
- 2026-10-29: the sweep may relabel a pull request while that pull request's own run is in flight in its own group; both read
  the same facts and write the same label, so the outcome is the same (due 2026-12-15).
- 2026-10-29: Q-309-2, the cancel-on-queue behaviour of a concurrency group is read from the runs above and GitHub's documentation, not
  from a test GitHub runs `(verify)` (due 2026-12-15).

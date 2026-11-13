# ADR-0499: A surviving governance run reads the draft state at run time

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: brief #1174, plan #661, brief #283, brief #216, ADR-0480
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`, `.github/`

## Context

The governance job skips its heavy steps (lint, the tests of the checks, the project tests) on a draft pull request
(brief #283) and reads the draft state from the event payload (`PR_DRAFT: ${{ github.event.pull_request.draft }}`).
A superseded pull request run is cancelled by its concurrency group (brief #216). A builder pushes and marks its pull
request ready within a second: the `synchronize` run carries `draft: true`, the `ready_for_review` run `draft: false`,
and the later one cancels the other. When the `synchronize` run survives it skips every heavy step and reports green.
Measured on #1171 at 4e6b5f1: run 43362621639 (ready state) cancelled, run 43362622556 (`PR_DRAFT: true`) green in
about 30 seconds with no tests; on 2026-11-12 and 2026-11-13 the conductor re-ran such a run by hand on seven pull
requests.

## Decision

1. The governance job reads the pull request's draft state when it runs, with one GET of `repos/{owner}/{repo}/pulls/<n>`
   in a step with id `draft` on `pull_request` events, before the first step that uses it, and every `PR_DRAFT` of the
   workflow is that step's output (`${{ steps.draft.outputs.draft }}`), never the payload's value alone.
2. `scripts/agk/pr_state.py --pull FILE [--event-draft true|false]` makes the decision from the saved answer: `true` only
   when the read says draft and the payload, when given, says draft too; else `false`. It fails closed: a missing,
   empty or unreadable answer, an error answer, or a `draft` that is not a JSON boolean is not a draft, so the heavy
   steps run. It reads a file only; the GET is the workflow's, as for the other reads of the job.
3. The workflow lines are the owner's: the builder proposes the exact steps on its pull request and the owner commits them.
   Nothing else changes: the concurrency group, the status-only skip and the edited run.

## Consequences

A pull request that is ready when its surviving run starts is checked in full, so nobody re-runs a cancelled run by
hand. A read that fails costs a full run, never a skipped one. A pull request turned back into a draft after its
`ready_for_review` event is still checked in full by that run. The `PR body shape` and `check_final_clearance` steps
read the same value, so they judge a ready pull request as ready.

## Residual

- 2026-11-13: `proof.yml` reads the payload's draft state the same way; this decision does not change it.

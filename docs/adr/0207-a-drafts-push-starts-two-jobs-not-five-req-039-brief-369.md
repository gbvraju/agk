# ADR-0207: a draft's push starts two jobs, not five, and a description edit starts no router run of its own (REQ-039, brief 369)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0165, ADR-0178
- Requirements: REQ-039

Protected classes: `.github/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #369 (split from #287, answers 1 and 2): GitHub bills every job as at least one whole minute. In a pilot on a private
Free-plan repository the router cost 28% of all minutes and proof 11%, mostly in jobs of a few seconds. A push to a draft
pull request started five jobs: governance (fast on drafts since #283), proof (its suite skipped at step level, but the job
still started), the router on `synchronize`, and the router again for each finished governance and proof run. A description
edit started three: `governance edited`, the router on `edited`, and the router again when `governance edited` finished.

## Decision

1. **Proof skips a draft at job level (answer 1).** `proof.yml` carries the job-level
   `if: github.event_name != 'pull_request' || !github.event.pull_request.draft`; `ready_for_review` and every push to a ready
   pull request run it in full. The step-level draft check of brief #283 stays as a second guard.
2. **The router starts no job where it cannot change a label (answer 2).** In `agk-route.yml` a `pull_request` event of a
   draft starts no job (a draft's governance run wakes the router when it finishes, and the `ready_for_review` governance run
   wakes it when the draft is marked ready); a `workflow_run` whose conclusion is `skipped` starts no job; and `edited`
   leaves the `pull_request` types, since the finished `governance edited` run wakes the router for the same state.
3. **Every other event keeps its job (answer 3).** Verdict, approval and correction comments, merges, pushes to the default
   branch and the runs of a ready pull request start what they started before. No required check is removed or weakened:
   `governance` and `proof` keep their names, and a skipped proof run never reports green over a failed run of the same head
   (`route.py`'s `latest_runs` ignores a skipped run while the name has another run).
4. **The workflows say why (answer 4)**, in their comments.
5. **Tests first (answer 5).** `tests/kit/test_ci_saving.py` reads the three workflow files, evaluates each job-level `if:`
   on a saved event, and counts the jobs an event starts, the router's wakes included: draft push 2, draft edit 2, ready push
   5 (unchanged), ready edit 2, `ready_for_review` 4 (unchanged), verdict comment 1 (unchanged).
   `tests/kit/test_route_triggers.py` checks that an edit is still labelled through the `governance edited` wake. The tests
   that pinned the router's `pull_request` types (`test_route.py`, `test_route_finishes.py`,
   `tests/kit_dev/test_route_finishes_install.py`) now pin the types without `edited`.

## Consequences

A draft costs two billed minutes per push instead of five, and a description edit two instead of three. A draft opened
without a push gets its label from the governance wake, a few seconds later than before. A workflow run whose every job was
skipped concludes `skipped` (verify), which is what lets the router ignore it.

## Residual

- 2026-10-30: SPEC-0032 rule 1 still lists `edited` among the router's `pull_request` types (it also predates `closed`, brief
  #302); whether the spec is amended is a reviewer's decision (Q-369-1).
- 2026-10-30: `(verify)` a workflow run whose only job is skipped concludes `skipped` (`workflow_run.conclusion == "skipped"`), and
  a draft push starts two jobs; the first live draft push after the merge confirms both.

## Log

- 2026-10-30, verdict on d3fd83c: fix list; the brief is met, and the `skipped`
  conclusion stays a `(verify)` residual until the first live draft push after the merge.

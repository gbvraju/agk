# ADR-0373: A scheduled sweep merges cleared pull requests, and an approved spec cannot merge as Draft

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0354, ADR-0263, amendment 144, brief #797
- Requirements: REQ-046

## Context

The merger job (ADR-0354) acts only on the pull request of one `issue_comment` or `workflow_run` event. An event that falls while the job cannot run is never sent again, and no later run looks at that pull request. Separately, SPEC-0052 merged reading `Draft` although its `Approve:` was posted: the approval and the merge raced the status commit, and neither the label nor the guarded merge read the spec's status.

This build changes the protected path classes `.github/` (the workflow `merger.yml`), `scripts/agk/`, `tests/kit/` and `kit/` (the installed copies through the manifest). A workflow change needs its own ADR (session rule 36).

## Decision

1. `merger.yml` gains `schedule` (every 15 minutes) and `workflow_dispatch`, and two jobs. `sweep-gate` holds no secret and reads `merge_cleared.py --sweep-gate`; `sweep`, in the `merge` environment, runs `merge_cleared.py --sweep`. The job `merger` of an event run is unchanged.
2. `--sweep` lists the open, non-draft pull requests labelled `agk:ready`, oldest first, and runs the one guarded merge on each cleared head, at most five a run, printing one line per pull request. It holds everything the guarded command holds; it adds no way to merge.
3. Each run prints `UNMERGED #<n> cleared <m> min <reason>` for a cleared pull request older than 20 minutes that it could not merge. In local mode `--sweep` merges nothing and prints only these lines. With `auto_merge` off, in personal mode or paused it reads nothing.
4. `merge_cleared.py` holds a pull request that adds or changes a spec a listed spec approver has approved while the spec on the head reads `Draft`, naming SPEC-0039 rule 5, and `route.py` keeps that pull request at `agk:approve`.

## Consequences

A cleared pull request is merged within one sweep of the event that was lost, and a head left unmerged is named in the run's log. A project without `[flow] auto_merge = true` runs only the short gate job every 15 minutes, which uses Actions minutes but no `merge` environment. An approval posted before the status commit now keeps the pull request waiting for that commit.

## Residual

- 2026-11-08: answers 1 and 2 of brief #797 are not built; the cause they name did not reproduce (`Q-797-1`). Until that is ruled, a `Verdict: fix list` with no findings stays `agk:fix` and is not cleared.
- 2026-11-08: five heads that stay held at the front of the list keep a sixth from being tried; it is reported by its `UNMERGED` line. Measure before raising the limit.
- 2026-11-08: the conductor's sweep line for `UNMERGED` comes with brief #776 build (c).

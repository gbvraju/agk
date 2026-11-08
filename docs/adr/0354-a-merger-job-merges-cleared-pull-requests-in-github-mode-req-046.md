# ADR-0354: A merger job merges cleared pull requests in GitHub mode (REQ-046)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0261, ADR-0265, ADR-0345, SPEC-0039, amendment 138, brief #765, plan #661
- Requirements: REQ-046

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0039 rule 2 has the conductor run `merge_cleared.py --pr <n> --sha <head>` when it clears a pull request. In
a scheduled conductor session that merge was refused by the `Main` ruleset (`[Merge Without Review]`, 2026-11-08
05:19Z, #732 and #746, merged later by hand, as the brief measures), so cleared work waited for a person. The owner
said yes to one workflow change for it (brief #765, quoted there as data, 2026-11-08). Rule 10 said the CI path adds no
workflow job; this decision changes that, for GitHub mode only.

## Decision

1. `.github/workflows/governance.yml` gains one job, `merger`. It starts on `issue_comment` (created) whose comment
   starts `Verdict:` or `Approve:` on a pull request, and on `workflow_run` of `governance` completed with
   `success` for a `pull_request` run. The `governance` job never runs on those two events, so the required check is
   unchanged; `workflow_dispatch` is added so the default branch's run can be started after a merge.
2. The job checks out the default branch (never the pull request's head) and runs three commands with its own token
   (`contents`, `pull-requests`, `issues` and `actions` write; `checks` and `statuses` read), no secret:
   `merge_cleared.py --event <payload> --event-name <event>` prints `<n> <sha>` or nothing; then exactly
   `python3 scripts/agk/merge_cleared.py --pr <n> --sha <sha>`, whose re-checks are unchanged; then
   `merge_cleared.py --report --pr <n> --sha <sha> --line <its line>`.
3. `--event` does nothing, and reads nothing from GitHub, unless `[flow] auto_merge = true` with `squash`, `execution`
   is not `local` and `forge` is not `files`, all on the default branch as checked out. It then names a pull request
   only when the open local-mode record issue is absent and the latest `Verdict:` comment reads
   `Verdict: cleared <head>`; otherwise it prints one line on stderr and nothing else.
4. `--report` dispatches the default branch's `governance` run after a merge (a merge by the job's token starts no
   workflow by itself) and posts one comment `merger: <line>` for a hold or a refusal, never the same line twice on
   one pull request. There is no retry loop; the next comment or green run is the next try.
5. `merge_cleared.py` names a merge that GitHub refuses for a ruleset violation `held: merge refused by the ruleset
   (rule 6)`, exit 3, so the owner sees it once until the GitHub Actions app is a bypass actor of `Main`.
6. Local mode (the conductor merges on the person's machine), personal mode (no merges) and `auto_merge = false` are
   unchanged; no extra account or seat.

## Consequences

- With the owner's bypass in place, a cleared head merges within minutes of its verdict or its green run, with no
  session; until then the job says once that the ruleset refused it, and the owner merges.
- The conductor's own run of the command stays; the sha-pinned merge stops a head merging twice, and the second run
  is refused or held.
- Every project with the installed workflow starts the job on a `Verdict:` or `Approve:` comment and on each green
  governance run of a pull request; with `auto_merge` off it ends at the setting, before any GitHub read.

## Residual

- 2026-11-08: that a workflow's `workflow_run` trigger fires on the completion of the same workflow, and the exact
  text GitHub gives a ruleset refusal of the merge call, are `(verify)`: observed in the documentation's examples,
  not tested against GitHub here (`Q-765-2`).
- 2026-11-08: principle 2 and session rule 2 name the conductor as the one runner of the command; whether they gain
  words for the job is the maintainers' (`Q-765-1`).
- 2026-11-08: the measurements of brief #765 answer 6 (minutes per run, time from verdict to merge on three pull
  requests) can be taken only after merge and the owner's bypass; they go in a later report.

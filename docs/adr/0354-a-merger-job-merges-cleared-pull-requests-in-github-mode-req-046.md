# ADR-0354: A merger job merges cleared pull requests in GitHub mode (REQ-046)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0261, ADR-0265, ADR-0345, SPEC-0039, amendment 139, brief #765, plan #661
- Requirements: REQ-046

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `kit/`

## Context

SPEC-0039 rule 2 has the conductor run `merge_cleared.py --pr <n> --sha <head>` when it clears a pull request. In
a scheduled conductor session that merge was refused by the session's own permission check (`[Merge Without Review]`,
2026-11-08 05:19Z, #732 and #746, merged later by hand, as the brief's `Measured:` line records it), so cleared work
waited for a person. The `Main` ruleset requires one approving review and lets only the admin role bypass it, and the
bypass list of a personal-account repository does not offer GitHub Actions (the `Correction:` on the brief,
2026-11-08), so the job's own token cannot merge either. The owner said yes to one workflow change for it (brief #765,
quoted there as data, 2026-11-08). Rule 10 said the CI path adds no
workflow job; this decision changes that, for GitHub mode only.

## Decision

1. A new workflow, `.github/workflows/merger.yml`, holds one job, `merger`; `governance.yml` does not change, so the
   required check does not either. The job starts on `issue_comment` (created) whose comment starts `Verdict:` or
   `Approve:` on a pull request, and on `workflow_run` of `governance` or `proof` completed with `success` for a
   `pull_request` run, so whichever required run ends last is a try. Both events run the file on the default branch,
   never a pull request's copy, and nothing starts the workflow from a `pull_request` or a push (the verdict on
   f3acd19, principle 9).
2. The job checks out the default branch (never the pull request's head) and runs three commands with its own token,
   which writes only comments (`issues` write; `contents`, `pull-requests`, `actions`, `checks` and `statuses` read):
   `merge_cleared.py --event <payload> --event-name <event>` prints `<n> <sha>` or nothing; then exactly
   `python3 scripts/agk/merge_cleared.py --pr <n> --sha <sha>`, whose re-checks are unchanged; then
   `merge_cleared.py --report --pr <n> --sha <sha> --line <its line>`. The secret `AGK_MERGE_TOKEN`, a fine-grained
   token the owner creates for this one repository (Contents and Pull requests, read and write), is stored as a secret
   of the GitHub environment `merge`, whose deployment branches are the default branch alone, and never as a repository
   secret. GitHub matches that rule against the run's `GITHUB_REF` and gives an environment's secrets only to a job that
   names it, so a run of any other ref cannot read it. It reaches only the second step, and the command uses it for its
   one merge call alone, so the merge runs under the owner's existing admin bypass and the ruleset stays as it is. The
   job reads it only from `secrets.AGK_MERGE_TOKEN`; no session handles it, and the tests of the merged code run under
   `env -i`. Without the secret the job posts one line `merge needs AGK_MERGE_TOKEN or the owner's tap`, once per pull
   request, and does nothing else. Owner step: create the environment `merge`, set its deployment branches to the default
   branch alone, and store the token there.
3. `--event` does nothing, and reads nothing from GitHub, unless `[flow] auto_merge = true` with `squash`, `execution`
   is not `local` and `forge` is not `files`, all on the default branch as checked out. It then names a pull request
   only when the open local-mode record issue is absent and the latest `Verdict:` comment reads
   `Verdict: cleared <head>`; otherwise it prints one line on stderr and nothing else.
4. `--report` writes nothing after a merge: the merge is made with `AGK_MERGE_TOKEN`, and its push starts the default
   branch's `governance` run by itself `(verify)`. It posts one comment `merger: <line>` for a hold or a refusal, never
   the same line twice on one pull request; `held: checks pending` posts nothing, since the other required run's end is
   the next try. There is no retry loop.
5. `merge_cleared.py` names a merge that GitHub refuses for a ruleset violation `held: merge refused by the ruleset
   (rule 6)`, exit 3, so the owner sees it once if the token cannot pass the ruleset.
6. Local mode (the conductor merges on the person's machine), personal mode (no merges) and `auto_merge = false` are
   unchanged; no extra account or seat.

## Consequences

- With the owner's secret in place, a cleared head merges within minutes of its verdict or its green run, with no
  session; until then the job says once that the merge needs the secret or the owner's tap, and the owner merges.
- The job's own token never merges: with the secret the secret merges, and without it nothing does. So the job holds no
  `contents` or `pull-requests` write and dispatches nothing.
- The conductor's own run of the command stays; the sha-pinned merge stops a head merging twice, and the second run
  is refused or held.
- Every project with the installed workflow starts the job (one billed minute or less) on a `Verdict:` or `Approve:`
  comment and on each green `governance` or `proof` run of a pull request; with `auto_merge` off it ends at the setting,
  before any GitHub read.
- The commands end green: a run of this workflow reports on the default branch's head, not on a pull request's.

## Residual

- 2026-11-08: the exact text GitHub gives a ruleset refusal of the merge call is `(verify)`: not tested against
  GitHub here (`Q-765-2`).
- 2026-11-08: principle 2 names the conductor as the one runner of the command. The maintainer ruled that the job may
  run it beside the conductor and that the owner's own pull request changes principle 2 (`Q-765-1`); until it merges the
  text of principle 2 and session rule 2 lags.
- 2026-11-08: the measurements of brief #765 answer 6 (minutes per run, time from verdict to merge on three pull
  requests) can be taken only after merge and the owner's secret; they go in a later report.
- 2026-11-08: the secret is out of a pull request's run only while the owner keeps it in the `merge` environment with
  that deployment rule; GitHub creates an environment a job names with no rule, and a repository secret of the same name
  would be readable by any run. Nothing here can check the owner's settings. Whoever can change the default branch's
  files can still change the job, under the ruleset and the protected class `.github/`; the owner holds the token's scope
  and expiry.

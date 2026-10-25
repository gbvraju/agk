# ADR-0137: CI runs only where it can change a result (REQ-039, brief #216)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0115, ADR-0122
- Requirements: REQ-039

Protected classes: `.github/`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #216 (priority 1 by the maintainer, Advances REQ-039, Size S; assigned to `builder-c` on #204). Measured on the last 100 runs of this repository: `proof` takes about 7 minutes and `governance` about 6 per run,
together about 82 of 109 minutes; the router runs on every comment, 32 of the 100 runs. Waste seen: a description edit re-runs the full proof suite; a new push leaves the run on the superseded commit going; every
pull request's status-only `Final:` commit re-runs the full suite; the router runs for comments that change no state. On a private repository these minutes are billed. The principles bind: no check that runs today is
lost on a commit that can change its result; the required check names `proof` and `governance` stay; generic; the workflows ship in the kit. ADR-0137 and amendment 73 were reserved on #216. The tests were written
first (`tests/kit/test_status_only.py`, `tests/kit/test_ci_saving.py`; before the code 45 of their cases failed).

## Decision

1. **proof** (`.github/workflows/proof.yml`): `edited` leaves its types (answer 1); `concurrency` with the group `proof-<pull request number>` and `cancel-in-progress: true` (answer 3); permissions are now
   `contents: read` and `checks: read`.
2. **The status-only final commit** (answer 4, `scripts/agk/status_only.py`, installed): a step reads, with one `gh api GET`, the conclusion of the `proof` check run on the parent of the head; the script prints
   `skip` only when the head has a single parent, the commit changes only modified files with exactly one removed and one added `- Status:` line each and no mode change, the conclusion was `success`, and the merge base
   with the default branch (`AGK_BASE`, else the default branch) is the parent's. Otherwise `run (<reason>)`, naming the condition and never a file, line or sha. On `skip` the suite step is skipped and the job reports
   the step `outcome: skipped`, so exactly one `outcome:` step still succeeds (`facts.py`). A failed GET leaves the conclusion empty and the suite runs. `governance` always runs in full on such a commit.
3. **governance** (`.github/workflows/governance.yml`): on `edited` only the steps that read the pull request body run (the base of the merge ref, the body file, the comments, the states of the pull requests,
   `check_specs`, `check_pr_mode`, the open briefs and the body shape); every other step carries the condition `github.event.action != 'edited'`, and the job and its name stay (answer 2). `concurrency` cancels a
   superseded run of a pull request and never a push to the default branch (answer 3).
4. **The router** (`.github/workflows/agk-route.yml`): the job-level `if` lets an `issue_comment` start a job only when the comment's first line starts with `Verdict:`, `Approve:`, `Approval:` or `Correction:`
   (answer 5); the other triggers are unchanged.
5. Amendment 73 (`docs/runs/proposed-spec-amendments-73.md`) is applied to SPEC-0010 rules 16 and 17, SPEC-0007 rule 13 and SPEC-0032 rule 1. The security guide lists the new permission. `kit/manifest.json` adds
   `scripts/agk/status_only.py`. A flow-mode fragment `changelog.d/req-039-ci-saving.md` records the change. The pull request changes `.github/workflows/`, so the maintainer merges it.

## Readings taken where the brief leaves a point open

Recorded as questions in the pull request, the most conservative reading each: a run of `governance` for an edited description has a concurrency group of its own (`...-edited`), because with the group of the brief a
description edit would cancel a full run of the same commit and the partial run would be left to report the required check; a status-only commit reports `outcome: skipped` (the outcome of the parent's proof is not
carried: it would need the steps of the parent's job); "proof passed on the parent" is the latest `proof` check run of the parent with the conclusion `success`; the merge base is compared with the base the workflow
already sets (`AGK_BASE`, the first parent of the merge ref).

## Consequences

- A description edit costs the partial governance run (about a minute) and no proof run; a superseded commit stops its runs; a status-only final commit costs governance and no suite; a comment that changes no state
  costs no router job.
- A required check can show two runs for one head (the full one and a partial one for an edited description); the partial one is a subset by construction, and a commit always has a full one.

## Residual

- 2026-10-25: the weekly report reads `proof` as `skipped` for a head that was skipped as status-only, though its parent was proven (due 2026-12-31).
- 2026-10-25: the saving is measured on the last 100 runs once; the next report should compare the minutes (due 2026-12-31).

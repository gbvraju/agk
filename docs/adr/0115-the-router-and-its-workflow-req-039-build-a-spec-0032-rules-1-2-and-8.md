# ADR-0115: the router and its workflow (REQ-039 build (a), SPEC-0032 rules 1, 2 and 8)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0110, ADR-0106
- Requirements: REQ-039

Protected classes: `.github/`, `kit/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0032 (Approved, #187) makes GitHub events, not sessions, compute the state of every pull request as one label. This is build (a) of rule 13: the router script and its workflow (rules 1, 2 and 8). Builds (b) to (e)
follow, each with its own ADR. The number ADR-0115 was reserved on #179 by the conductor. The tests were written first (`tests/kit/test_route.py`); before `route.py` existed they could not be collected.

## Decision

1. **The workflow** `.github/workflows/agk-route.yml` (installed verbatim; a new protected file of class `.github/`): triggers `pull_request` (opened, synchronize, reopened, edited), `issue_comment` (created),
   `workflow_run` (completed, for `governance` and `proof`, the workflows of the kit that hold the checks) and `push`, the last guarded by the default branch as `governance.yml` is. Permissions are exactly
   `contents: read`, `pull-requests: write`, `issues: write`, `checks: read` and `statuses: read` (the verdict on #187 added the last two). One job, `agk-route`, checks out the default branch
   (`ref: github.event.repository.default_branch`), so no code of a pull request runs, then runs `python3 scripts/agk/route.py` with `GH_TOKEN` set to the job's `GITHUB_TOKEN`. No agent, no model, no listener to a
   label change; a concurrency group serialises the runs.
2. **The script** `scripts/agk/route.py` (installed verbatim, class `scripts/agk/`): reads with GET the pull request, the check runs and statuses of its head, its comments, reviews and changed files, and sets exactly one
   of `agk:ci-running`, `agk:ci-red`, `agk:conflict`, `agk:review`, `agk:fix`, `agk:approve`, `agk:ready`, removing the other six; it creates a missing label and writes nothing else (no comment, review, merge or
   issue; the only writes are POST and DELETE on label endpoints). The order when several states hold is the one of SPEC-0032 rule 2 (ruled on #187). It routes the pull request an event names, every open pull
   request on a push to the default branch or a finished workflow of the default branch, and nothing for a comment on an issue; `--pr N` and `--all` route by hand and `--dry-run` writes nothing.
3. **Readings taken where the spec leaves a point open** (recorded as questions in the pull request, the most conservative reading each): the required checks are every check run and commit status of the head except
   the router's own job; a head with no check run yet is `agk:ci-running`; `failure`, `timed_out`, `cancelled`, `action_required`, `startup_failure` and `stale` are red, `skipped` and `neutral` are not; a verdict of
   kind `rejected` that names the head is `agk:fix`; `agk:ready` is a `cleared` verdict naming the head or a head covered in advance (`metrics.covered_head`), with green checks and no conflict; `agk:approve` replaces
   `agk:ready` while a spec the pull request sets to `Approved` has no `Approve: <sha> SPEC-<n>` first line in a comment or review of an account in `spec_approvers` of `config/reviewers.yaml` (the key is read here and
   defined by build (c); absent, nobody approves and the label stays `agk:approve`); the pull request files must be readable (else the router writes nothing and fails naming the rule), reviews and statuses may be
   unreadable and count as none. A merged or closed pull request keeps its last label.
4. **Installed**: both files are added to `verbatim` in `kit/manifest.json`; `docs/guides/security.md` lists the workflow and its permissions; the tests of the kit are `tests/kit/test_route.py`. A flow-mode
   fragment `changelog.d/req-039-a-router.md` records the change.

## Consequences

- A project that installs or upgrades gets a fifth workflow that writes labels with the workflow token; the notice of `init` and `adopt` about `issues: write` is not changed (the router creates no issue).
- Builds (b) to (e) can read the label with one GET. Until build (c) defines `spec_approvers`, a pull request that sets a spec `Approved` stays `agk:approve`.

## Residual

- 2026-10-25: sessions and people share one account until lane F, so `agk:approve` cannot tell a person's `Approve:` from a session's; SPEC-0032 rule 6 and the conductor role file carry it (due 2026-12-31).
- 2026-10-25: the workflows that hold the required checks are named in the workflow file as `governance` and `proof`; a project that renames them edits the file (due 2026-12-31).

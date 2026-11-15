# ADR-0575: `check_adrs.py --pending` reads the records a merge of main brought in

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: brief #1370, found bug #1266, release #1258, ADR-0277, ADR-0501, plan #661
- Requirements: REQ-050

## Context

A release pull request flips the `- Status: Proposed` line of each ADR that a verified Final record accepted
(SPEC-0021 rule 3a, ADR-0277); `check_adrs.py --pending --comments FILE` lists them. Found bug #1266: `--pending`
read only the records in HEAD's first-parent history (`final_records(root, "HEAD")`). The squash commits that a
merge of main brings into a release branch sit on the merge's second parent, so `--pending` printed nothing, while
`check_release.py`, which reads the merge base, found them and failed with `rule 5: an ADR of docs/adr/ that a Final
line accepted still says Proposed`. Release #1258 (0.64.4) worked around it by running `--pending` in a worktree
of main. `--record-ids --body FILE` already reads HEAD and the merge base for a release pull request (ADR-0501).

## Decision

`check_adrs.py --pending` reads the verified records of HEAD's history and of the merge base with the default
branch (the base `--base`, `AGK_BASE`, `GITHUB_BASE_REF` or the default branch gives, as the other modes resolve
it), and lists each ADR that any of them accepted and whose file still says `Proposed`, once, in file order. When no
base resolves (outside CI, no default branch) it reads HEAD alone, as before. A base that resolves but has no merge
base with HEAD fails with the shared message, as the other modes do. A record of the merge base is verified exactly
as one of HEAD's: its Final comment must be in FILE, and without FILE, while any record exists, it fails closed.

Protected path classes changed: `scripts/agk/` (`check_adrs.py`), `tests/kit/` (`test_check_adrs.py`) and
`docs/adr/` (this file).

## Consequences

A release branch that merged main learns of every pending flip from `--pending` before `check_release.py` fails on
it, without a worktree of main. `--pending` on a branch with no such merge lists as before. The comments FILE must
hold the Final comments of the merge base's records too: `--record-ids --body FILE` already prints them for a
release pull request.

## Residual

- 2026-11-15: `--record-ids` without `--body` still prints only HEAD's records; whether it should add the merge
  base's is Q-1370-1 on the pull request.

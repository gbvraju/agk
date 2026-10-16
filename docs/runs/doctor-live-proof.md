# Doctor: live proof on the sandbox (for the maintainers; not run by the agent)

Date: 2026-10-15 (from `date -u`). SPEC-0006 rule 18, criterion b of ADR-0015. Run on `gbvraju/agk-sandbox` with an account that
has admin rights and `gh auth login`. The doctor itself changes nothing; the steps below change the sandbox's settings on
purpose, one at a time, and restore each. Nothing here touches `gbvraju/colorama` or `tartley/colorama`.

## Setup

```
git clone git@github.com:gbvraju/agk-sandbox.git && cd agk-sandbox
python3 /path/to/agk/scripts/agk/doctor.py --kit-root /path/to/agk
```

`/path/to/agk` is a checkout of the kit at the version in the sandbox's `agk.toml` (or the installed plugin root, whose
`kit_version` must equal `version` in `agk.toml`; otherwise the vendored checks print `??` with the reason
`version-mismatch`). `--repo gbvraju/agk-sandbox` is read from `origin` when omitted.

## Step 0: the correctly configured sandbox

Expected: `summary: 20 ok, 0 fail, 0 cannot-check` and exit 0 (`echo $?`). If `placeholder-team-*` fails, replace the
placeholder first (`python3 scripts/agk/reviewers.py --codeowners --write`). Record the full output.

## Steps 1 to 10: one misconfiguration at a time

For each row: make the change, run the doctor, check that exactly the listed id is `FAIL` and everything else is unchanged, then
restore. Record the command, the output and the exit code.

| # | Change | Expected `FAIL` | Exit | Restore |
| --- | --- | --- | --- | --- |
| 1 | Settings, Rules, delete the ruleset (export it first) | `ruleset-missing` (the other ruleset checks print `??` `no-ruleset`) | 1 | re-import the ruleset |
| 2 | Set the ruleset enforcement to Disabled | `ruleset-enforcement` | 1 | Active |
| 3 | Add a bypass actor | `ruleset-bypass` | 1 | remove it |
| 4 | Remove "restrict deletions" | `ruleset-deletion` | 1 | add it |
| 5 | Remove "require linear history" | `ruleset-linear-history` | 1 | add it |
| 6 | Remove "block force pushes" | `ruleset-force-push` | 1 | add it |
| 7 | Allow merge commits in the pull request rule | `ruleset-pull-request` | 1 | squash only |
| 8 | Remove `governance` from the required status checks | `required-check-governance` | 1 | add it |
| 9 | Replace the team in `config/reviewers.yaml` with `@REPLACE-ME` (working tree only, do not commit) | `placeholder-team-reviewers` | 1 | `git checkout config/reviewers.yaml` |
| 10 | `git remote set-head origin --delete` | `origin-head` | 4 | `git remote set-head origin main` |
| 11 | `gh workflow disable drift-audit.yml` | `drift-workflow-state` | 1 | `gh workflow enable drift-audit.yml` |
| 12 | Delete the `schedule:` block from `.github/workflows/drift-audit.yml` (working tree only) | `drift-workflow-file` | 1 | `git checkout .github/workflows/drift-audit.yml` |
| 13 | Edit a line of `scripts/agk/check_adrs.py` (working tree only) | `vendored-differs` | 1 | `git checkout scripts/agk/check_adrs.py` |
| 14 | Turn off "Allow auto-merge" in Settings | `repo-auto-merge` | 4 | on |

Also expected: a stricter ruleset (one required approval, a team approver) keeps `20 ok`.

## Step 15: not an admin

Run the doctor with an account that has write access but no admin rights, or `GH_TOKEN` of a read-only token. Expected: the ruleset
checks print `??` with `no-admin` (never `ruleset-missing`), exit 4. With `gh` logged out: every remote check prints `??`
`gh-unauthenticated`, exit 4.

## Record

Add `docs/runs/doctor-live-proof-1.md` with the date, the sandbox commit, the kit version, and per step: the change, the
`FAIL` ids seen, the exit code, and that it was restored. Criterion b is met when steps 0 to 14 match and 15 prints `??`.

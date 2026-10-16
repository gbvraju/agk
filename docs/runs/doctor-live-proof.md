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


## Baseline run on the upgraded sandbox (2026-10-16)

Date: 2026-10-16 (from `date -u`). The baseline of the live proof, run after the sandbox's upgrade pull request (#4) was merged and before any
setting is changed. Read-only: `gh api` GET through the doctor, plus the direct GET reads below; nothing was changed, and the doctor wrote
nothing.

| Item | Value |
| --- | --- |
| Sandbox | `gbvraju/agk-sandbox`, a fresh clone of `main` at `b4fce6f` (`chore: upgrade the kit from 0.1.0 to 0.9.0 (agk upgrade) (#4)`), `refs/remotes/origin/HEAD` is `refs/remotes/origin/main` |
| Kit | `/home/user/agk` at `main` `2497161` (PR #42), `kit_version` 0.9.0; the sandbox's `agk.toml` has `version = "0.9.0"` |
| Account | the session's `gh` (credentials attached with push access for the live proofs); `permissions.admin` is `true` on the repository |
| Command | `python3 /home/user/agk/scripts/agk/doctor.py --repo gbvraju/agk-sandbox --kit-root /home/user/agk`, run from the clone |

Output, verbatim:

```
agk doctor 0.9.0
ok ruleset-missing error a ruleset targets the default branch
ok ruleset-enforcement error ruleset enforcement is active
ok ruleset-bypass error ruleset has no bypass actors
ok ruleset-target error the ruleset targets the default branch
ok ruleset-deletion error ruleset restricts deletions
ok ruleset-linear-history error ruleset requires linear history
ok ruleset-force-push error ruleset blocks force pushes
ok ruleset-pull-request error ruleset requires a pull request
ok required-check-governance error the status check `governance` is required
ok repo-auto-merge warn repository setting allow_auto_merge is on
ok repo-delete-branch warn repository setting delete_branch_on_merge is on
ok placeholder-team-reviewers error config/reviewers.yaml has no placeholder team
ok placeholder-team-codeowners error .github/CODEOWNERS has no placeholder team
ok origin-head warn refs/remotes/origin/HEAD exists
ok drift-workflow-file error .github/workflows/drift-audit.yml has a schedule
ok drift-workflow-state error the drift-audit workflow is active
ok kit-version warn the kit version equals version in agk.toml
ok vendored-missing error every vendored file is present
ok vendored-differs error every vendored file equals the kit's copy
ok default-branch-config warn default_branch in agk.toml equals the repository's default branch
summary: 20 ok, 0 fail, 0 cannot-check
exit 0
```

All 20 checks are `ok` and the exit code is 0. No check printed `FAIL` or `??`, so there is no failure to explain: the sandbox's baseline is the
correctly configured repository of SPEC-0006 rule 16.

Corroborating direct reads (GET) on the same day, the same facts the doctor read:

```
GET repos/gbvraju/agk-sandbox
{"allow_auto_merge":true,"default_branch":"main","delete_branch_on_merge":true,"permissions":{"admin":true,"maintain":true,"pull":true,"push":true,"triage":true}}
GET repos/gbvraju/agk-sandbox/rulesets
[{"enforcement":"active","id":25107038,"name":"Main","target":"branch"}]
GET repos/gbvraju/agk-sandbox/rulesets/25107038 (selected fields)
enforcement active; bypass_actors []; conditions.ref_name include ["~DEFAULT_BRANCH"], exclude [];
rules: deletion, non_fast_forward, required_linear_history,
       pull_request (required_approving_review_count 0, dismiss_stale_reviews_on_push true, allowed_merge_methods ["squash"]),
       required_status_checks (context "governance")
GET repos/gbvraju/agk-sandbox/actions/workflows/drift-audit.yml
{"path":".github/workflows/drift-audit.yml","state":"active"}
```

The workflows of the sandbox are `drift-audit`, `governance` and `metrics`, all `active`.

Next (the maintainers' step, one change at a time; the agent re-runs the doctor and records each run verbatim in this file): the table of steps 1 to 14
above, each followed by its restore. The agent changes no setting.

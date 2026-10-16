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


## Local cases (2026-10-16)

Done before run 1, on the baseline clone only (`/home/user/sandbox-baseline`, never pushed), each restored afterwards. The command of every run is the
baseline command, from the clone: `python3 /home/user/agk/scripts/agk/doctor.py --repo gbvraju/agk-sandbox --kit-root /home/user/agk`. The output is
verbatim, the full report; the expected failed ids are those of the brief.

| Case | Change | Restore | Expected | Observed | Match |
| --- | --- | --- | --- | --- | --- |
| L1 | `@gbvraju` replaced by `@REPLACE-ME` in `config/reviewers.yaml` and `.github/CODEOWNERS` | `git checkout -- config/reviewers.yaml .github/CODEOWNERS` | `placeholder-team-reviewers`, `placeholder-team-codeowners` | the same two `FAIL`, exit 1 | match |
| L2 | `git remote set-head origin --delete` | `git remote set-head origin main` (no network) | `origin-head` | `origin-head` `FAIL`, exit 4 (a warning) | match |
| L3 | one line appended to `scripts/agk/check_adrs.py` (a vendored file) | `git checkout -- scripts/agk/check_adrs.py` | `vendored-differs` | `vendored-differs` `FAIL` naming that path, exit 1 | match |
| L4 | `version = "0.8.0"` in `agk.toml` | `git checkout -- agk.toml` | `kit-version` | `kit-version` `FAIL`; `vendored-missing` and `vendored-differs` `??` (`version-mismatch`), as SPEC-0006 rule 8 says; exit 4 | match |

### L1

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
FAIL placeholder-team-reviewers error config/reviewers.yaml still names the placeholder team
  fix: replace the placeholder with a real team or user, then run `python3 scripts/agk/reviewers.py --codeowners --write`
FAIL placeholder-team-codeowners error .github/CODEOWNERS still names the placeholder team
  fix: replace the placeholder with a real team or user, then run `python3 scripts/agk/reviewers.py --codeowners --write`
ok origin-head warn refs/remotes/origin/HEAD exists
ok drift-workflow-file error .github/workflows/drift-audit.yml has a schedule
ok drift-workflow-state error the drift-audit workflow is active
ok kit-version warn the kit version equals version in agk.toml
ok vendored-missing error every vendored file is present
ok vendored-differs error every vendored file equals the kit's copy
ok default-branch-config warn default_branch in agk.toml equals the repository's default branch
summary: 18 ok, 2 fail, 0 cannot-check
exit 1
```

### L2

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
FAIL origin-head warn refs/remotes/origin/HEAD is missing
  fix: run `git remote set-head origin <default_branch>` (no network; `-a` asks the remote)
ok drift-workflow-file error .github/workflows/drift-audit.yml has a schedule
ok drift-workflow-state error the drift-audit workflow is active
ok kit-version warn the kit version equals version in agk.toml
ok vendored-missing error every vendored file is present
ok vendored-differs error every vendored file equals the kit's copy
ok default-branch-config warn default_branch in agk.toml equals the repository's default branch
summary: 19 ok, 1 fail, 0 cannot-check
exit 4
```

### L3

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
FAIL vendored-differs error vendored files differ from the kit's copy (scripts/agk/check_adrs.py)
  fix: review `git log -p -- <path>`; restore the kit's copy, or record the deliberate edit in an ADR that names the path class
ok default-branch-config warn default_branch in agk.toml equals the repository's default branch
summary: 19 ok, 1 fail, 0 cannot-check
exit 1
```

### L4

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
FAIL kit-version warn the kit version differs from version in agk.toml
  fix: run /agk:upgrade (SPEC-0008)
?? vendored-missing error cannot check (version-mismatch)
  to check: use a kit of the same version as version in agk.toml, or run /agk:upgrade
?? vendored-differs error cannot check (version-mismatch)
  to check: use a kit of the same version as version in agk.toml, or run /agk:upgrade
ok default-branch-config warn default_branch in agk.toml equals the repository's default branch
summary: 17 ok, 1 fail, 2 cannot-check
exit 4
```

### After the four restores

`git status -sb` of the clone: `## main...origin/main` (clean); `refs/remotes/origin/HEAD` is `refs/remotes/origin/main`. The doctor again:

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


## Run 1 (2026-10-16)

The maintainers' change: the ruleset was set to disabled (read back with GET: `enforcement` is `disabled`). Command (from the baseline clone, `/home/user/sandbox-baseline`, unchanged): `python3 /home/user/agk/scripts/agk/doctor.py --repo gbvraju/agk-sandbox --kit-root /home/user/agk`.
Direct GET read before the run: `GET repos/gbvraju/agk-sandbox/rulesets` gives `[{"enforcement":"disabled","id":25107038}]`. With no active ruleset the bypass check and every element check fail (ADR-0017 decision 2; the rule that only an active ruleset protects).

| Expected failed ids | Observed failed ids | Match |
| --- | --- | --- |
| `ruleset-enforcement` plus every element check | `ruleset-enforcement`, `ruleset-bypass`, `ruleset-deletion`, `ruleset-linear-history`, `ruleset-force-push`, `ruleset-pull-request`, `required-check-governance` (13 ok, 7 fail, 0 cannot-check, exit 1; `ruleset-missing` and `ruleset-target` stay ok: a branch ruleset still targets the default branch) | match |

Output, verbatim:

```
agk doctor 0.9.0
ok ruleset-missing error a ruleset targets the default branch
FAIL ruleset-enforcement error ruleset: enforcement is not active
  fix: set the ruleset to Active
FAIL ruleset-bypass error ruleset: bypass_actors is not empty
  fix: remove every bypass actor
ok ruleset-target error the ruleset targets the default branch
FAIL ruleset-deletion error ruleset: the deletion rule is missing
  fix: restrict deletions
FAIL ruleset-linear-history error ruleset: the required_linear_history rule is missing
  fix: require linear history
FAIL ruleset-force-push error ruleset: the non_fast_forward rule is missing
  fix: block force pushes
FAIL ruleset-pull-request error ruleset: pull_request rule missing, stale approvals not dismissed on push, or merge commits allowed
  fix: require a pull request, dismiss stale approvals on push, and do not allow merge commits (ADR-0001 decision 3 uses squash only)
FAIL required-check-governance error ruleset: the required status check `governance` is missing
  fix: require the status check `governance`
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
summary: 13 ok, 7 fail, 0 cannot-check
exit 1
```


## Run 2 (2026-10-16)

The maintainers' change: a bypass actor was added to the ruleset (read back with GET: `enforcement` `active`, `bypass_actors` `[{"actor_id":5,"actor_type":"RepositoryRole","bypass_mode":"always"}]`). Command (from the baseline clone, `/home/user/sandbox-baseline`, unchanged): `python3 /home/user/agk/scripts/agk/doctor.py --repo gbvraju/agk-sandbox --kit-root /home/user/agk`.
The ruleset is active again (run 1's change was restored); the bypass actor is the only difference from the baseline.

| Expected failed ids | Observed failed ids | Match |
| --- | --- | --- |
| `ruleset-bypass` | `ruleset-bypass` only (19 ok, 1 fail, 0 cannot-check, exit 1) | match |

Output, verbatim:

```
agk doctor 0.9.0
ok ruleset-missing error a ruleset targets the default branch
ok ruleset-enforcement error ruleset enforcement is active
FAIL ruleset-bypass error ruleset: bypass_actors is not empty
  fix: remove every bypass actor
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
summary: 19 ok, 1 fail, 0 cannot-check
exit 1
```


## Run 3 (2026-10-16)

The maintainers' change: `governance` was removed from the ruleset's required status checks (read back with GET: the `required_status_checks` rule is still there with an empty list of contexts; `enforcement` `active`, `bypass_actors` `[]`, rules deletion, non_fast_forward, required_linear_history, pull_request, required_status_checks). Command (from the baseline clone, `/home/user/sandbox-baseline`, unchanged): `python3 /home/user/agk/scripts/agk/doctor.py --repo gbvraju/agk-sandbox --kit-root /home/user/agk`.
Run 2's bypass actor was restored (`bypass_actors` is `[]` again); the empty required-checks list is the only difference from the baseline.

| Expected failed ids | Observed failed ids | Match |
| --- | --- | --- |
| `required-check-governance` | `required-check-governance` only (19 ok, 1 fail, 0 cannot-check, exit 1) | match |

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
FAIL required-check-governance error ruleset: the required status check `governance` is missing
  fix: require the status check `governance`
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
summary: 19 ok, 1 fail, 0 cannot-check
exit 1
```


## Run 4 (2026-10-16)

The maintainers' change: merge commits were allowed in the ruleset's pull request rule (read back with GET: `allowed_merge_methods` `["squash","merge"]`, `dismiss_stale_reviews_on_push` `true`, `required_approving_review_count` `0`; `enforcement` `active`, `bypass_actors` `[]`, required check `governance` back). Command (from the baseline clone, `/home/user/sandbox-baseline`, unchanged): `python3 /home/user/agk/scripts/agk/doctor.py --repo gbvraju/agk-sandbox --kit-root /home/user/agk`.
Run 3's change was restored (the required check `governance` is back). The merge method list is the only difference from the baseline; `merge` in it is what fails the check (SPEC-0006 rule 7: only `merge` allowed fails; squash alone, or squash and rebase, passes).

| Expected failed ids | Observed failed ids | Match |
| --- | --- | --- |
| `ruleset-pull-request` | `ruleset-pull-request` only (19 ok, 1 fail, 0 cannot-check, exit 1) | match |

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
FAIL ruleset-pull-request error ruleset: pull_request rule missing, stale approvals not dismissed on push, or merge commits allowed
  fix: require a pull request, dismiss stale approvals on push, and do not allow merge commits (ADR-0001 decision 3 uses squash only)
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
summary: 19 ok, 1 fail, 0 cannot-check
exit 1
```


## Run 5 (2026-10-16)

The maintainers' change: the drift-audit workflow was disabled (read back with GET: `state` `disabled_manually`; `governance` and `metrics` stay `active`). Command (from the baseline clone, `/home/user/sandbox-baseline`, unchanged): `python3 /home/user/agk/scripts/agk/doctor.py --repo gbvraju/agk-sandbox --kit-root /home/user/agk`.
Run 4's change was restored (the ruleset's `allowed_merge_methods` is `["squash"]` again). `drift-workflow-file` stays ok: the file and its schedule are unchanged; only the state on GitHub differs. This confirms one of the `(verify)` facts of SPEC-0006: a workflow disabled by hand reads `disabled_manually`; `disabled_inactivity` is still not observed.

| Expected failed ids | Observed failed ids | Match |
| --- | --- | --- |
| `drift-workflow-state` | `drift-workflow-state` only (19 ok, 1 fail, 0 cannot-check, exit 1) | match |

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
FAIL drift-workflow-state error the drift-audit workflow is not active on GitHub
  fix: enable the workflow (GitHub disables scheduled workflows after inactivity (verify))
ok kit-version warn the kit version equals version in agk.toml
ok vendored-missing error every vendored file is present
ok vendored-differs error every vendored file equals the kit's copy
ok default-branch-config warn default_branch in agk.toml equals the repository's default branch
summary: 19 ok, 1 fail, 0 cannot-check
exit 1
```


## Run 6 (2026-10-16)

The maintainers' change: auto-merge was to be turned off in the repository settings; GitHub still reports it on (read back with GET before the run and again about 20 seconds later: `allow_auto_merge` `true`, `delete_branch_on_merge` `true`, `allow_squash_merge`, `allow_merge_commit` and `allow_rebase_merge` all `true`; the repository's `updated_at` is `2026-10-16T06:24:26Z`, the time of the sandbox merge, so no settings change has been recorded since). Command (from the baseline clone, `/home/user/sandbox-baseline`, unchanged): `python3 /home/user/agk/scripts/agk/doctor.py --repo gbvraju/agk-sandbox --kit-root /home/user/agk`.
Run 5's change was restored (the drift-audit workflow `state` is `active`). The doctor reported what GitHub reports: `allow_auto_merge` is still on, so `repo-auto-merge` is correctly `ok`. The mismatch is with the expectation, not with the check: the setting change does not appear to have been applied (not saved, or made on another setting or repository). The same run was repeated once after the second read and printed the same summary (`20 ok, 0 fail, 0 cannot-check`). Run 6 needs the change to be made (or confirmed) and "Run 6" said again.

| Expected failed ids | Observed failed ids | Match |
| --- | --- | --- |
| `repo-auto-merge`, exit 4 | none (20 ok, 0 fail, 0 cannot-check, exit 0) | **mismatch** |

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


## Run 6, second attempt (2026-10-16)

The maintainers' change: auto-merge was turned off in the repository settings (read back with GET: `allow_auto_merge` `false`, `delete_branch_on_merge` `true`). Command (from the baseline clone, `/home/user/sandbox-baseline`, unchanged): `python3 /home/user/agk/scripts/agk/doctor.py --repo gbvraju/agk-sandbox --kit-root /home/user/agk`.
This is the second attempt at run 6; the first one (above) found the setting still on and is kept as it was. The drift-audit workflow `state` is `active` (run 5 restored). The repository's `updated_at` still reads `2026-10-16T06:24:26Z`: it is not moved by this setting, so it cannot date the change.

| Expected failed ids | Observed failed ids | Match |
| --- | --- | --- |
| `repo-auto-merge`, exit 4 | `repo-auto-merge` only (19 ok, 1 fail, 0 cannot-check, exit 4, a warning) | match |

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
FAIL repo-auto-merge warn repository setting allow_auto_merge is off
  fix: allow auto-merge
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
summary: 19 ok, 1 fail, 0 cannot-check
exit 4
```

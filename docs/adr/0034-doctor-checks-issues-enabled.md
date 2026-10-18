# ADR-0034: doctor fails when Issues are off and an issue-writing workflow is installed; init and adopt warn, kit 0.17.0

- Status: Accepted
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0015, ADR-0030
- Requirements: REQ-002, REQ-009, REQ-010

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`

## Context

The pilot repository had Issues disabled (a fork has them off by default). The metrics, the drift audit and the product report each
write one GitHub issue per run, so each would fail on every run, and nothing told the people who installed them. The doctor read the
workflow state (`drift-workflow-state`) but not the setting the workflows depend on.

## Decision

1. **A new doctor check `issues-disabled`** (SPEC-0006 amendment, `docs/runs/proposed-spec-amendments-21.md`, applied here): severity
   `error`; it fails when the repository setting `has_issues` is false and any of `.github/workflows/metrics.yml`, `drift-audit.yml`,
   `product-report.yml` exists in the repository. It reads `has_issues` from the repository response the doctor already fetches: no new
   read, no new path. It is `ok` when none of the three files exists (nothing writes an issue), or Issues are on; `cannot-check` with the
   reason class when the repository read fails, and with `bad-response` when the response has no `has_issues`. The message names the
   setting and the installed files; the fix says to enable Issues (General, Features) or delete those files.
2. **`init` and `adopt` print a warning** after the existing notice about workflows with `issues: write`: those workflows need Issues
   enabled; with Issues disabled they fail; `agk doctor` checks it. They read no setting (neither touches the network); the warning is
   printed whatever the setting is. SPEC-0011 rule 17 is amended for the second line.
3. **Fixtures and tests**: `issues-disabled` (fails, names `drift-audit.yml`), `issues-disabled-no-workflows` (ok), `issues-unknown`
   (`cannot-check`); `has_issues: true` is added to the four recorded repository responses (a real response always has it); a test that
   the failure names all three files when all three are installed; a test of the exit code (the failure exits 1); and a
   test that init and adopt print the warning. The counts of the doctor tests (twenty-one checks) are updated.
4. **Kit 0.17.0**: `doctor.py`, `test_doctor.py` and the fixtures are installed files, so the minor version moves; manifest, hashes and
   plugin version follow. The kit-only `init.py` carries the warning.

## The live proof (2026-10-18, read-only)

Only `GET` requests were made (the repository, its rulesets and the drift-audit workflow of `gbvraju/agk-sandbox`, with the token of the
session; no write, no setting changed, nothing in the sandbox clone touched: `git status` there stays empty). The recorded responses
were passed to the doctor of this branch with `--api-dir` and the local sandbox clone as ROOT (its kit is 0.9.0, so the vendored-file
checks read `cannot-check`; that is not the subject here). The sandbox has `metrics.yml` and `drift-audit.yml` installed.

```
$ python3 scripts/agk/doctor.py --api-dir <live responses> --repo gbvraju/agk-sandbox --kit-root <this branch> <sandbox clone>
ok drift-workflow-file error .github/workflows/drift-audit.yml has a schedule
ok drift-workflow-state error the drift-audit workflow (and the product-report workflow, where installed) is active
ok issues-disabled error Issues are enabled, or no workflow that writes issues is installed
summary: 18 ok, 1 fail, 2 cannot-check
```

The repository response says `"has_issues": true`, so the check reads `ok`. The failing reading, on a **copy** of that response with
`has_issues` set to false (an edited file, not a live setting; no repository of the maintainers has Issues off, and turning them off is
a write this proof does not make); the doctor exits 1 on it (on the live response it exits 4: the two `cannot-check` are the vendored-file checks of the kit-0.9.0 sandbox):

```
FAIL issues-disabled error repository setting has_issues is off and workflows that write issues are installed (metrics.yml, drift-audit.yml)
  fix: enable Issues in the repository settings (General, Features), or delete the workflow files that write issues (.github/workflows/metrics.yml, drift-audit.yml, product-report.yml)
```

## Consequences

- A repository that installed the workflows and has Issues off now fails the doctor with exit 1 (Q-K4-162): with Issues disabled every
  issue-writing workflow fails silently, so the kit's weekly outputs are lost; a warning was ignored for two days on the pilot.
- Every install and upgrade to 0.17.0 carries the new check and its fixtures; `agk upgrade` replaces the installed doctor.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-162 ruled | Severity of the new check. | `error` (the maintainers' ruling; the first reading was `warn`): with Issues disabled every issue-writing workflow fails silently, so the weekly outputs are lost, and a warning was ignored for two days on the pilot; the doctor exits 1 on this failure |
| Q-K4-163 ruled | A repository with none of the three workflows installed. | `ok` without needing the setting (even if the read fails), so a repository that deleted them is never nagged |
| Q-K4-164 ruled | The kit version. | 0.17.0: `doctor.py`, `test_doctor.py` and the fixtures are installed files and a check is added (a minor change) |
| Q-K4-165 ruled | Where the warning is printed. | by `print_branch_rules`, after the existing issues notice, so both init and adopt print it, once, with no GitHub read |

## Residual

- 2026-10-18: the doctor does not read whether Actions are enabled on the repository (a fork has them off until enabled); the
  workflow-state check covers the workflows that exist on GitHub, not that case (due 2026-12-31).

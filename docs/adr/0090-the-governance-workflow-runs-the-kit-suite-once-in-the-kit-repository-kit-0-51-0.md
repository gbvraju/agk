# ADR-0090: the governance workflow runs the kit suite once in the kit repository (issue #147), kit 0.51.0

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0081, ADR-0050
- Requirements: REQ-009

Protected classes: `.claude-plugin/`, `.github/`, `agk.toml`, `kit/`, `tests/kit/`

## Context

`.github/workflows/governance.yml` (installed verbatim) runs `Tests of the checks` (`make -f agk.mk agk-test`) and then `Project tests` (`make -f agk.mk agk-project-test`). In a project the first prints that the
kit's own tests are not installed and takes seconds. In the kit repository both run the same suite, because `agk.toml` `project_tests` is the kit suite on purpose (the proof job runs it as the project's tests), so every kit
pull request spent about four extra minutes (issue #147).

Measured on the last three successful `pull_request` runs of the governance workflow of this repository (GET of the run and job records, 2026-10-24):

| Run | `governance` job | `Tests of the checks` | `Project tests` |
| --- | --- | --- | --- |
| 40088884076 | 479 s | 239 s | 224 s |
| 40087749900 | 458 s | 227 s | 217 s |
| 40085813403 | 470 s | 231 s | 220 s |

## Decision

1. The `Project tests` step gets `if: ${{ hashFiles('kit/agk-kit.mk') == '' }}`: it runs only where the kit's own suite is not installed. The condition reads the tree, not the name of the repository. In a project
   `kit/agk-kit.mk` is absent and the step runs as now.
2. The proof workflow is not changed; it still runs `project_tests` through `proof.py`.
3. Tests first (`tests/kit/test_workflow.py`): the step carries the condition and nothing else changed, `Tests of the checks` has none, the condition does not name the repository, and the proof workflow has no such
   condition and `project_tests` still holds the suite (before the change: 1 failed, 19 passed).
4. Amendment 47 (`docs/runs/proposed-spec-amendments-47.md`) is applied to SPEC-0002 rule 5.
5. **Kit 0.51.0**: the manifest `kit_version`, the hashes (`governance.yml` is installed verbatim), the plugin version and `version` in this repository's `agk.toml`.

## Consequences

- A kit pull request spends about four minutes fewer in the governance job (to be read from the first run of the pull request that makes this change, the first "after" run).
- A project changes nothing it runs.

## Residual

None.

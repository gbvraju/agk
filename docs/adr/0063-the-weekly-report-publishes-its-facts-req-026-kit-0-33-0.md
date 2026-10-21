# ADR-0063: the weekly report publishes the facts it was rendered from (REQ-026, SPEC-0019), kit 0.33.0

- Status: Accepted
- Date: 2026-10-21
- Deciders: maintainers
- Related: ADR-0060, ADR-0061, ADR-0053
- Requirements: REQ-026

Protected classes: `.github/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

PR A3 of the portal Part A (ADR-0060 decision 4). REQ-026 was taken in by intake (ADR-0061) and SPEC-0019 was Approved with its two open questions ruled (Q-S0019-1: the upload sets the action's overwrite
option; Q-S0019-2: the current major release of the upload action pinned by its full commit SHA, looked up at the build). The read-only slice of the portal reads the facts document, which until now was
written to the runner's temporary directory and lost with the job. This ADR builds the artifact, tests first: the tests for AC1 to AC8 were written and run on unchanged `main` before any change (9 failed,
18 passed, the 18 being the existing workflow tests and two guards; the output is in the pull request body).

## Decision

1. **The step** (SPEC-0019 rules 1 to 3): `.github/workflows/product-report.yml` gains a last step, `Publish the facts of the report`, that uses `actions/upload-artifact` pinned to the full commit SHA
   `cf430e030ddbb5b0abf93d22962f4752f3646cd9` (tag `v7.0.2`, which is also `v7`, the current major release; looked up with `git ls-remote` on 2026-10-21), with `name: agk-facts-<week>`, `path` the file
   `facts.py` wrote (`${{ runner.temp }}/facts.json`), `retention-days: 90`, `if-no-files-found: error` and `overwrite: true`. It comes after the step that writes the issue and has no condition: it runs
   when the issue was written.
2. **The week label** (Q-S0019-2): the report step has `id: report` and writes `week=<label>` to `$GITHUB_OUTPUT` once it has checked the label; the upload step reads `steps.report.outputs.week`.
3. **An empty file never reaches the issue or the upload** (rule 4): the report step fails, writing nothing, when the facts file is missing or empty (`[ ! -s "$facts" ]`), before the report is made. A
   missing file at the upload fails the run through `if-no-files-found: error`; the issue already written stays (no step closes, deletes or rolls back an issue).
4. **A re-run** (rule 5, Q-S0019-1): the README of the pinned version says of `overwrite`: "If true, an artifact with a matching name will be deleted before a new one is uploaded. If false, the action
   will fail if an artifact for the given name already exists. Does not fail if the artifact does not exist. Optional. Default is 'false'", and "Although it's not possible to mutate an Artifact, can
   completely overwrite one. But do note that this will give the Artifact a new ID, the previous one will no longer exist". So a re-run attempt of the same run replaces the artifact of that name, which is
   the action's own deletion of the same-named artifact of that run; the workflow deletes nothing else and has no delete step.
5. **Access and writes** (rules 6 and 7): the artifact is readable by those who can read the repository's workflow runs; no release, page, gist, link or other place; the `permissions` block is unchanged and
   the workflow commits and pushes nothing.
6. **Nothing else changes** (rule 8): `facts.py`, `product_report.py`, the report, the issue and its label, the inbox and `metrics.yml` are byte-identical. The existing workflow test counts three
   `exit 1` in the report step instead of two (the empty-facts guard), and its helpers stop the shell body at the next step and give it a `GITHUB_OUTPUT` file.
7. **Amendment 30** (`docs/runs/proposed-spec-amendments-30.md`) is applied to SPEC-0011 rule 15 (the steps). The security guide's table of what each workflow may write gains the artifact in the
   `product-report.yml` row.
8. **Tests** (`tests/kit/test_product_report_facts_artifact.py`, new): the step, its name, order, pin, retention, strictness and overwrite; the file at the upload path equal to the fixture byte for byte; an empty
   facts file failing the shell body with no `gh` call; the permissions and writes unchanged; no other upload or publication; the security guide row; `metrics.yml` unchanged.
9. **Kit 0.33.0**: the manifest `kit_version`, the hash of `.github/workflows/product-report.yml`, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). No file is added to or
   removed from the manifest.

## Consequences

- Each weekly run keeps its facts for 90 days as a file of the run; the portal's read-only slice reads it with a token that can read the repository's runs.
- The workflow now uses a second action; its `action.yml` runs it on Node 24 (`using: 'node24'`).
- The pilot gets this on its next `agk upgrade`, after its week W44 is scored on 2026-11-02.

## Questions

none

## Residual

- 2026-10-21: the first scheduled run after the merge shows the artifact on its run page; the maintainers download it and compare it with the report of that week (due 2026-11-30).

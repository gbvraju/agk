# ADR-0030: the weekly product report workflow, its installation and the doctor's coverage (SPEC-0011 (b)), kit 0.16.0

- Status: Proposed
- Date: 2026-10-17
- Deciders: maintainers
- Related: ADR-0021, ADR-0025, ADR-0029
- Requirements: REQ-017, REQ-018

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`

## Context

ADR-0029 added the renderer. This pull request makes it run: the workflow of SPEC-0011 rules 15 to 17, installed by default, with
the doctor covering it (Q-K4-52). ADR-0025 sets the date that matters: the report must reach the pilot repository by 2026-10-31,
so that its first scheduled run is Monday 2026-11-02. What is left after this merges is the pilot's own upgrade, which the
maintainers run from `docs/runs/pilot-upgrade-brief.md`, and the live run in this repository.

## Decision

1. **`.github/workflows/product-report.yml`**, as SPEC-0011 rule 15: name `product-report`; Mondays 07:13 UTC (`13 7 * * 1`) and
   `workflow_dispatch` with an optional `today`; `contents`, `pull-requests`, `checks` and `actions` read and `issues` write; one job,
   only on the default branch, actions pinned to a full commit SHA, a full checkout. It runs `facts.py` into a file, `product_report.py`
   on that file, and creates or edits the one issue of the week (rule 16): `agk product report YYYY-Www`, label `agk-product-report`,
   the body replaced. `gh` is used only for `issue create`, `issue edit` and `label create`. The week and the title come from the
   first line of the report (no second computation of the week in shell); an empty or malformed first line writes nothing and fails.
2. **Installed by default.** The workflow, `tests/kit/test_product_report_workflow.py` and the doctor fixtures are verbatim files in
   `kit/manifest.json`, so `init`, `adopt` and `upgrade` install them as they do the other workflows. The notice that `init` and `adopt`
   print about workflows with `issues: write` names three workflows.
3. **`inbox_hours = 48`** is in both `agk.toml` templates (new installs). An existing target keeps its `agk.toml` (upgrade sets the
   `version` line only); its facts read `inbox_hours` as 48 when the key is absent (SPEC-0009 rule 7), so nothing changes for it.
4. **SPEC-0006 is amended** (Q-K4-52, `docs/runs/proposed-spec-amendments-19.md`, applied here): `drift-workflow-state` reads the
   state of the product-report workflow as well, where `.github/workflows/product-report.yml` exists in ROOT, and fails when either
   workflow is not `active`. No new check id. A repository that deleted the file is reported by `vendored-missing`, as for any
   verbatim file; nothing is read for it. The doctor makes a fifth read (`GET` of the workflow) only in that case.
5. **Kit 0.16.0**: the manifest, the hashes and the plugin version. `docs/runs/pilot-upgrade-brief.md` is written for the pilot
   session; it names no repository.
6. **The live proof is a follow-up docs pull request**: a `workflow_dispatch` run needs the workflow on the default branch (its
   guard is that branch), so it cannot run before this merges. After the merge the run is made on this repository with the day's
   date, and the issue number and the five headings, verbatim, are recorded in `docs/runs/product-report-live-1.md` (Q-K4-143).

## Consequences

- Every installed repository gets a third issue-writing workflow at its next `agk upgrade`; deleting the file removes it.
- The report's first scheduled run in this repository is Monday 2026-10-19 07:13 UTC if this merges before; the pilot's is
  Monday 2026-11-02 if its upgrade merges by 2026-10-31.
- The doctor's report for a repository with the workflow installed has one more read; a repository without it reads exactly the
  four paths of SPEC-0006.

## Questions

| Q | Question | Reading taken (conservative) |
| --- | --- | --- |
| Q-K4-143 | The brief wants the live run recorded in this pull request; a new workflow cannot be dispatched before it is on the default branch. | the live run and `docs/runs/product-report-live-1.md` are a docs pull request after the merge; this one carries the workflow's tests, run against a stub `gh` and a fixture |
| Q-K4-144 | Rule 6 of SPEC-0006 names four reads; a fifth is needed for the state of the second workflow. | the fifth read is made only where the file exists; a non-active state fails the check even when the other workflow could not be read |
| Q-K4-145 | Rule 15 shows `facts.py --today "$today"`; the repository is otherwise taken from `origin`. | the workflow also passes `--repo "$GITHUB_REPOSITORY"` (no guess from a remote URL); `--print-action` prints one or two lines, the first is the action and the second a notice |
| Q-K4-146 | A target that was installed before this kit has no `inbox_hours`. | no change to its `agk.toml`; the facts default of 48 applies |
| Q-K4-147 | The brief asks for a "dry run" of the report in the pilot; the workflow has no dry-run mode and its one write is the issue. | the pilot brief renders locally from `facts.py` first (writes nothing), then dispatches once, which creates or updates the week's issue |

## Residual

- 2026-10-17: the live run of this workflow in this repository is not done by this pull request (due 2026-10-31).
- 2026-10-17: whether GitHub disables the scheduled workflow after inactivity is `(verify)` (SPEC-0011 residual, due 2026-11-23); a
  disabled workflow is what `drift-workflow-state` now also reports for this one.
- 2026-10-17: the pilot's upgrade, the first scheduled run there (2026-11-02) and the two weeks of answers (criterion a) are the
  maintainers' and the pilot session's steps, not this repository's (due 2026-11-30).

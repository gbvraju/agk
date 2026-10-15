# ADR-0016: Per-PR metrics: the build of SPEC-0007

- Status: Proposed
- Date: 2026-10-15
- Deciders: maintainers
- Related: ADR-0002, ADR-0011, ADR-0012, ADR-0015
- Amends: ADR-0002
- Requirements: REQ-012

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `docs/requirements.md`

## Context

SPEC-0007 (Approved on 2026-10-15) defines per-PR metrics for K3 criterion d of ADR-0015: every field derived after the
pull request closes, a weekly issue written by its own run, and the verdict-comment convention that makes review
rounds, rejection and the cleared head derivable. Building it changes protected paths: a new workflow, a new
script and its tests (`.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`), the manifest (`kit/`), the
`governance` workflow, and the text of REQ-012 (`docs/requirements.md`). ADR-0002 says metrics are "recorded in the PR
body"; SPEC-0007 rule 1 derives them instead, so ADR-0002 is amended on that point only.

## Decision

1. **REQ-012's acceptance text is amended** (rulings Q-K3-35 and Q-K3-34) to four criteria: AC1 each closed pull request
   has a derived record of rejections, blocked weakenings, deviations and cost class; AC2 the record also carries hours
   open to merge, review rounds, protected classes touched, ADRs added, tests before and after, and whether the merged
   head was cleared; AC3 a weekly issue lists every pull request closed in the week; AC4 the cost class is the
   maintainers' review cost, derived from fix-list rounds and hours open to merge (S: 0 rounds and under 24 h; M: at
   most 2 rounds and under 72 h; L: anything else or closed unmerged; unknown when the rounds are unknown). The Status
   stays `planned`.
2. **The metrics are derived, not recorded in the PR body** (amends ADR-0002, which said "recorded in the PR body"):
   `scripts/agk/metrics.py` reads the GitHub REST API (`gh api`, GET only, no credential held by the script) and local
   git objects after the close. `check_pr_body.py` is unchanged. The one human input is the `Verdict:` comment line
   of SPEC-0007 rule 4, relayed by the implementation session (a relayed record, not a signed one).
3. **The weekly record is one GitHub issue per ISO week** written by `.github/workflows/metrics.yml` (Monday 06:43 UTC
   and `workflow_dispatch` with `today`), labelled `agk-metrics`, with the permissions of SPEC-0007 rule 17. An empty
   week is still written. A week whose listed and recorded counts differ is flagged `INCOMPLETE` and fails the job.
4. **`governance.yml` is split into one step per check**, each named by its check id (`check_protected_changes`,
   `check_requirements`, `check_adrs`, `check_specs`, `check_neutrality`, `check_build_state`, `check_kit_tests`,
   `reviewers --check`, `reviewers --check-codeowners`), so a failing check is readable from the check run. The job
   name `governance`, and so the required status check, is unchanged. `make governance` and
   `make -f agk.mk agk-governance` are unchanged; a test keeps the steps equal to that recipe.
5. **The workflow is installed by default** by init and adopt, as the drift audit is, with its script, tests and the JSON
   fixtures of SPEC-0007 rule 20 (all listed in `kit/manifest.json`). Both commands print a notice that the workflows
   write issues with the workflow token (`issues: write`).
6. **Kit version 0.7.0** (the next minor, one bump for this item).

## Consequences

- `blocked_weakenings` is `unknown` for pull requests whose head commits ran the old single `Governance checks` step;
  it becomes known from this change onward.
- The manifest lists the fixture files one by one (the law-files test requires every tracked file under `tests/kit/`),
  so targets receive about 140 small JSON files.
- Targets that cannot create issues or labels see the workflow fail; they delete the workflow file.
- The first run for the window is started by hand after merge; see `docs/runs/metrics-first-run.md`.

## Residual

- 2026-10-15: whether the check run id equals the Actions job id for every check run `(verify)`: confirmed for one
  run of this repository by a GET on 2026-10-15; the script treats a missing job as unknown (due 2026-11-15).
- 2026-10-15: the check-runs list is read with `per_page=100`, enough for the `governance` run of one commit
  (due 2026-12-31).

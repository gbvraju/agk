# Upgrade: live proof on the sandbox (criterion c of ADR-0015)

Date: 2026-10-16 (from `date -u`). SPEC-0008 rule 23, criterion c. Run by the agent after the maintainers approved attaching
`gbvraju/agk-sandbox` with push access and ruled Q-K3-71 (a). Rules kept: no repository setting changed, no merge, no push to the
default branch, work only through a branch and a pull request; `gbvraju/colorama` and `tartley/colorama` untouched.

| Item | Value |
| --- | --- |
| Kit | this repository at `main` `2497161` (PR #42), `kit_version` 0.9.0 |
| Sandbox | `gbvraju/agk-sandbox`, default branch `main` at `88337bd`, a kit 0.1.0 install (no `agk.toml`; `[tool.agk] version = "0.1.0"` in `pyproject.toml`) |
| Clone and branch | `/home/user/agk-sandbox`, branch `agk-upgrade-0.9.0` |
| Sandbox pull request | https://github.com/gbvraju/agk-sandbox/pull/4 (open, against `main`; not merged) |
| Commit | `b417482` `chore: upgrade the kit from 0.1.0 to 0.9.0 (agk upgrade) with ADR-0003` |

## Result in one paragraph

The dry run and the real run printed the same lines (267 files; 17 `replace`, 250 `create` including `agk.toml`; no `conflict`,
`deleted-locally` or `removed-in-kit`). `git ls-files -s` before and after: the 46 tracked files are all still tracked, none was
removed, no mode changed, 18 changed (17 vendored kit files and `.github/CODEOWNERS`), 251 were added (250 kit files and ADR-0003). No
product file changed: `README.md`, `pyproject.toml`, `src/wordcount.py` and `tests/test_wordcount.py` are byte for byte the same, and so
are all of `docs/` and `config/` that existed. `make governance` failed once on `.github/CODEOWNERS` (the 0.1.0 rendering had duplicate
lines), passed after the command the upgrade printed (`python3 scripts/agk/reviewers.py --codeowners --write`) was run, and passes on the
final commit. A second run of the upgrade says `nothing to do`.

## The commands

```
cd /home/user/agk && git checkout main && git pull --ff-only origin main      # 2497161
git clone https://github.com/gbvraju/agk-sandbox /home/user/agk-sandbox
cd /home/user/agk-sandbox && git checkout -b agk-upgrade-0.9.0 && git ls-files -s > before.txt   # 46 lines
cd /home/user/agk && python3 scripts/agk/upgrade.py /home/user/agk-sandbox --dry-run
cd /home/user/agk && python3 scripts/agk/upgrade.py /home/user/agk-sandbox
cd /home/user/agk-sandbox && git add -A && git ls-files -s > after.txt                          # 297 lines at the end
```

## Dry run, verbatim

```
unchanged .claude/agents/drift-auditor.md
create .claude/agents/reviewer.md
replace .claude/hooks/stop_check.py
replace .claude/settings.json
unchanged .github/PULL_REQUEST_TEMPLATE.md
create .github/workflows/drift-audit.yml
replace .github/workflows/governance.yml
create .github/workflows/metrics.yml
unchanged .gitignore
replace CLAUDE.md
replace Makefile
create agk.mk
create agk.toml
replace constitution/principles.md
unchanged docs/adr/TEMPLATE.md
unchanged docs/briefs/TEMPLATE.md
unchanged docs/specs/TEMPLATE.md
replace scripts/agk/check_adrs.py
unchanged scripts/agk/check_build_state.py
create scripts/agk/check_kit_tests.py
unchanged scripts/agk/check_neutrality.py
unchanged scripts/agk/check_pr_body.py
replace scripts/agk/check_protected_changes.py
replace scripts/agk/check_requirements.py
create scripts/agk/check_review_report.py
create scripts/agk/check_specs.py
replace scripts/agk/common.py
create scripts/agk/config.py
create scripts/agk/doctor.py
create scripts/agk/drift_audit.py
create scripts/agk/metrics.py
create scripts/agk/review_context.py
replace scripts/agk/reviewers.py
replace scripts/agk/traceability.py
replace tests/kit/conftest.py
create tests/kit/drift_fixtures.py
create tests/kit/fixtures/doctor/auto-merge-off/api/repo.json
create tests/kit/fixtures/doctor/auto-merge-off/case.json
create tests/kit/fixtures/doctor/bypass-actor/api/ruleset-1.json
create tests/kit/fixtures/doctor/bypass-actor/case.json
create tests/kit/fixtures/doctor/bypass-on-disabled-ruleset/api/ruleset-2.json
create tests/kit/fixtures/doctor/bypass-on-disabled-ruleset/api/rulesets.json
create tests/kit/fixtures/doctor/bypass-on-disabled-ruleset/case.json
create tests/kit/fixtures/doctor/default-branch-mismatch/case.json
create tests/kit/fixtures/doctor/default-branch-mismatch/tree/agk.toml
create tests/kit/fixtures/doctor/delete-branch-off/api/repo.json
create tests/kit/fixtures/doctor/delete-branch-off/case.json
create tests/kit/fixtures/doctor/disabled-holds-every-rule/api/ruleset-1.json
create tests/kit/fixtures/doctor/disabled-holds-every-rule/api/ruleset-2.json
create tests/kit/fixtures/doctor/disabled-holds-every-rule/api/rulesets.json
create tests/kit/fixtures/doctor/disabled-holds-every-rule/case.json
create tests/kit/fixtures/doctor/drift-disabled/api/workflow-drift-audit.json
create tests/kit/fixtures/doctor/drift-disabled/case.json
create tests/kit/fixtures/doctor/drift-no-schedule/case.json
create tests/kit/fixtures/doctor/drift-no-schedule/tree/.github/workflows/drift-audit.yml
create tests/kit/fixtures/doctor/excluded-default-branch/api/ruleset-1.json
create tests/kit/fixtures/doctor/excluded-default-branch/case.json
create tests/kit/fixtures/doctor/excluded-default-ref/api/ruleset-1.json
create tests/kit/fixtures/doctor/excluded-default-ref/case.json
create tests/kit/fixtures/doctor/merge-commits-allowed/api/ruleset-1.json
create tests/kit/fixtures/doctor/merge-commits-allowed/case.json
create tests/kit/fixtures/doctor/no-admin-empty-list/api/repo.json
create tests/kit/fixtures/doctor/no-admin-empty-list/api/rulesets.json
create tests/kit/fixtures/doctor/no-admin-empty-list/case.json
create tests/kit/fixtures/doctor/no-admin/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-admin/case.json
create tests/kit/fixtures/doctor/no-deletion/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-deletion/case.json
create tests/kit/fixtures/doctor/no-dismiss-stale/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-dismiss-stale/case.json
create tests/kit/fixtures/doctor/no-force-push-block/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-force-push-block/case.json
create tests/kit/fixtures/doctor/no-governance-check/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-governance-check/case.json
create tests/kit/fixtures/doctor/no-linear-history/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-linear-history/case.json
create tests/kit/fixtures/doctor/no-origin-head/case.json
create tests/kit/fixtures/doctor/no-ruleset/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-ruleset/api/rulesets.json
create tests/kit/fixtures/doctor/no-ruleset/case.json
create tests/kit/fixtures/doctor/ok/api/repo.json
create tests/kit/fixtures/doctor/ok/api/ruleset-1.json
create tests/kit/fixtures/doctor/ok/api/rulesets.json
create tests/kit/fixtures/doctor/ok/api/workflow-drift-audit.json
create tests/kit/fixtures/doctor/ok/case.json
create tests/kit/fixtures/doctor/ok/kit/.claude/hooks/x.txt
create tests/kit/fixtures/doctor/ok/kit/kit/manifest.json
create tests/kit/fixtures/doctor/ok/kit/scripts/agk/y.txt
create tests/kit/fixtures/doctor/ok/tree/.claude/hooks/x.txt
create tests/kit/fixtures/doctor/ok/tree/.github/CODEOWNERS
create tests/kit/fixtures/doctor/ok/tree/.github/workflows/drift-audit.yml
create tests/kit/fixtures/doctor/ok/tree/agk.toml
create tests/kit/fixtures/doctor/ok/tree/config/reviewers.yaml
create tests/kit/fixtures/doctor/ok/tree/scripts/agk/y.txt
create tests/kit/fixtures/doctor/placeholder-codeowners/case.json
create tests/kit/fixtures/doctor/placeholder-codeowners/tree/.github/CODEOWNERS
create tests/kit/fixtures/doctor/placeholder-reviewers/case.json
create tests/kit/fixtures/doctor/placeholder-reviewers/tree/config/reviewers.yaml
create tests/kit/fixtures/doctor/stricter-ok/api/ruleset-1.json
create tests/kit/fixtures/doctor/stricter-ok/case.json
create tests/kit/fixtures/doctor/target-all/api/ruleset-1.json
create tests/kit/fixtures/doctor/target-all/case.json
create tests/kit/fixtures/doctor/vendored-edited/case.json
create tests/kit/fixtures/doctor/vendored-edited/tree/.claude/hooks/x.txt
create tests/kit/fixtures/doctor/vendored-missing/case.json
create tests/kit/fixtures/doctor/version-mismatch/case.json
create tests/kit/fixtures/doctor/version-mismatch/tree/agk.toml
create tests/kit/fixtures/doctor/weak-enforcement/api/ruleset-1.json
create tests/kit/fixtures/doctor/weak-enforcement/api/rulesets.json
create tests/kit/fixtures/doctor/weak-enforcement/case.json
create tests/kit/fixtures/doctor/wrong-target/api/ruleset-1.json
create tests/kit/fixtures/doctor/wrong-target/case.json
create tests/kit/fixtures/metrics/cleared-other-commit/checks-0067000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cleared-other-commit/comments-103.json
create tests/kit/fixtures/metrics/cleared-other-commit/commits-103.json
create tests/kit/fixtures/metrics/cleared-other-commit/files-103.json
create tests/kit/fixtures/metrics/cleared-other-commit/jobs-10030.json
create tests/kit/fixtures/metrics/cleared-other-commit/pull-103.json
create tests/kit/fixtures/metrics/cleared-other-commit/pulls.json
create tests/kit/fixtures/metrics/closed-unmerged/checks-0069000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/closed-unmerged/comments-105.json
create tests/kit/fixtures/metrics/closed-unmerged/commits-105.json
create tests/kit/fixtures/metrics/closed-unmerged/files-105.json
create tests/kit/fixtures/metrics/closed-unmerged/jobs-10050.json
create tests/kit/fixtures/metrics/closed-unmerged/pull-105.json
create tests/kit/fixtures/metrics/closed-unmerged/pulls.json
create tests/kit/fixtures/metrics/cost-classes/checks-006f000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cost-classes/checks-0070000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cost-classes/checks-0071000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cost-classes/checks-0072000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cost-classes/checks-0073000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cost-classes/comments-111.json
create tests/kit/fixtures/metrics/cost-classes/comments-112.json
create tests/kit/fixtures/metrics/cost-classes/comments-113.json
create tests/kit/fixtures/metrics/cost-classes/comments-114.json
create tests/kit/fixtures/metrics/cost-classes/comments-115.json
create tests/kit/fixtures/metrics/cost-classes/commits-111.json
create tests/kit/fixtures/metrics/cost-classes/commits-112.json
create tests/kit/fixtures/metrics/cost-classes/commits-113.json
create tests/kit/fixtures/metrics/cost-classes/commits-114.json
create tests/kit/fixtures/metrics/cost-classes/commits-115.json
create tests/kit/fixtures/metrics/cost-classes/files-111.json
create tests/kit/fixtures/metrics/cost-classes/files-112.json
create tests/kit/fixtures/metrics/cost-classes/files-113.json
create tests/kit/fixtures/metrics/cost-classes/files-114.json
create tests/kit/fixtures/metrics/cost-classes/files-115.json
create tests/kit/fixtures/metrics/cost-classes/jobs-10110.json
create tests/kit/fixtures/metrics/cost-classes/jobs-10120.json
create tests/kit/fixtures/metrics/cost-classes/jobs-10130.json
create tests/kit/fixtures/metrics/cost-classes/jobs-10140.json
create tests/kit/fixtures/metrics/cost-classes/jobs-10150.json
create tests/kit/fixtures/metrics/cost-classes/pull-111.json
create tests/kit/fixtures/metrics/cost-classes/pull-112.json
create tests/kit/fixtures/metrics/cost-classes/pull-113.json
create tests/kit/fixtures/metrics/cost-classes/pull-114.json
create tests/kit/fixtures/metrics/cost-classes/pull-115.json
create tests/kit/fixtures/metrics/cost-classes/pulls.json
create tests/kit/fixtures/metrics/empty-week/pulls.json
create tests/kit/fixtures/metrics/files/checks-0079000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/files/comments-121.json
create tests/kit/fixtures/metrics/files/commits-121.json
create tests/kit/fixtures/metrics/files/files-121.json
create tests/kit/fixtures/metrics/files/jobs-10210.json
create tests/kit/fixtures/metrics/files/pull-121.json
create tests/kit/fixtures/metrics/files/pulls.json
create tests/kit/fixtures/metrics/fix-lists-cleared/checks-0066000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/fix-lists-cleared/checks-006600cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/fix-lists-cleared/checks-006601cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/fix-lists-cleared/comments-102.json
create tests/kit/fixtures/metrics/fix-lists-cleared/commits-102.json
create tests/kit/fixtures/metrics/fix-lists-cleared/files-102.json
create tests/kit/fixtures/metrics/fix-lists-cleared/jobs-10020.json
create tests/kit/fixtures/metrics/fix-lists-cleared/jobs-10021.json
create tests/kit/fixtures/metrics/fix-lists-cleared/jobs-10022.json
create tests/kit/fixtures/metrics/fix-lists-cleared/pull-102.json
create tests/kit/fixtures/metrics/fix-lists-cleared/pulls.json
create tests/kit/fixtures/metrics/governance-split/checks-0083000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/governance-split/checks-008300cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/governance-split/checks-008301cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/governance-split/comments-131.json
create tests/kit/fixtures/metrics/governance-split/commits-131.json
create tests/kit/fixtures/metrics/governance-split/files-131.json
create tests/kit/fixtures/metrics/governance-split/jobs-10310.json
create tests/kit/fixtures/metrics/governance-split/jobs-10311.json
create tests/kit/fixtures/metrics/governance-split/jobs-10312.json
create tests/kit/fixtures/metrics/governance-split/pull-131.json
create tests/kit/fixtures/metrics/governance-split/pulls.json
create tests/kit/fixtures/metrics/governance-unsplit/checks-0084000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/governance-unsplit/checks-008400cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/governance-unsplit/comments-132.json
create tests/kit/fixtures/metrics/governance-unsplit/commits-132.json
create tests/kit/fixtures/metrics/governance-unsplit/files-132.json
create tests/kit/fixtures/metrics/governance-unsplit/jobs-10320.json
create tests/kit/fixtures/metrics/governance-unsplit/jobs-10321.json
create tests/kit/fixtures/metrics/governance-unsplit/pull-132.json
create tests/kit/fixtures/metrics/governance-unsplit/pulls.json
create tests/kit/fixtures/metrics/incomplete/checks-00a1000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/incomplete/comments-161.json
create tests/kit/fixtures/metrics/incomplete/commits-161.json
create tests/kit/fixtures/metrics/incomplete/files-161.json
create tests/kit/fixtures/metrics/incomplete/jobs-10610.json
create tests/kit/fixtures/metrics/incomplete/pull-161.json
create tests/kit/fixtures/metrics/incomplete/pulls.json
create tests/kit/fixtures/metrics/missing-comments/checks-0097000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/missing-comments/commits-151.json
create tests/kit/fixtures/metrics/missing-comments/files-151.json
create tests/kit/fixtures/metrics/missing-comments/jobs-10510.json
create tests/kit/fixtures/metrics/missing-comments/pull-151.json
create tests/kit/fixtures/metrics/missing-comments/pulls.json
create tests/kit/fixtures/metrics/no-verdict-merged/checks-0065000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/no-verdict-merged/checks-006500cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/no-verdict-merged/comments-101.json
create tests/kit/fixtures/metrics/no-verdict-merged/commits-101.json
create tests/kit/fixtures/metrics/no-verdict-merged/files-101.json
create tests/kit/fixtures/metrics/no-verdict-merged/jobs-10010.json
create tests/kit/fixtures/metrics/no-verdict-merged/jobs-10011.json
create tests/kit/fixtures/metrics/no-verdict-merged/pull-101.json
create tests/kit/fixtures/metrics/no-verdict-merged/pulls.json
create tests/kit/fixtures/metrics/verdict-rejected/checks-0068000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/verdict-rejected/comments-104.json
create tests/kit/fixtures/metrics/verdict-rejected/commits-104.json
create tests/kit/fixtures/metrics/verdict-rejected/files-104.json
create tests/kit/fixtures/metrics/verdict-rejected/jobs-10040.json
create tests/kit/fixtures/metrics/verdict-rejected/pull-104.json
create tests/kit/fixtures/metrics/verdict-rejected/pulls.json
create tests/kit/fixtures/metrics/verdict-suffix/checks-00ab000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/verdict-suffix/comments-171.json
create tests/kit/fixtures/metrics/verdict-suffix/commits-171.json
create tests/kit/fixtures/metrics/verdict-suffix/files-171.json
create tests/kit/fixtures/metrics/verdict-suffix/jobs-10710.json
create tests/kit/fixtures/metrics/verdict-suffix/pull-171.json
create tests/kit/fixtures/metrics/verdict-suffix/pulls.json
create tests/kit/fixtures/metrics/window-edges/checks-008d000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/window-edges/checks-008e000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/window-edges/checks-008f000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/window-edges/checks-0090000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/window-edges/comments-141.json
create tests/kit/fixtures/metrics/window-edges/comments-142.json
create tests/kit/fixtures/metrics/window-edges/comments-143.json
create tests/kit/fixtures/metrics/window-edges/comments-144.json
create tests/kit/fixtures/metrics/window-edges/commits-141.json
create tests/kit/fixtures/metrics/window-edges/commits-142.json
create tests/kit/fixtures/metrics/window-edges/commits-143.json
create tests/kit/fixtures/metrics/window-edges/commits-144.json
create tests/kit/fixtures/metrics/window-edges/files-141.json
create tests/kit/fixtures/metrics/window-edges/files-142.json
create tests/kit/fixtures/metrics/window-edges/files-143.json
create tests/kit/fixtures/metrics/window-edges/files-144.json
create tests/kit/fixtures/metrics/window-edges/jobs-10410.json
create tests/kit/fixtures/metrics/window-edges/jobs-10420.json
create tests/kit/fixtures/metrics/window-edges/jobs-10430.json
create tests/kit/fixtures/metrics/window-edges/jobs-10440.json
create tests/kit/fixtures/metrics/window-edges/pull-141.json
create tests/kit/fixtures/metrics/window-edges/pull-142.json
create tests/kit/fixtures/metrics/window-edges/pull-143.json
create tests/kit/fixtures/metrics/window-edges/pull-144.json
create tests/kit/fixtures/metrics/window-edges/pulls.json
create tests/kit/pytest.ini
create tests/kit/review_fixtures.py
create tests/kit/test_agk_config.py
create tests/kit/test_agk_mk.py
unchanged tests/kit/test_check_adrs.py
unchanged tests/kit/test_check_build_state.py
create tests/kit/test_check_kit_tests.py
unchanged tests/kit/test_check_neutrality.py
unchanged tests/kit/test_check_pr_body.py
unchanged tests/kit/test_check_protected_changes.py
replace tests/kit/test_check_requirements.py
create tests/kit/test_check_specs.py
create tests/kit/test_doctor.py
create tests/kit/test_drift_audit.py
create tests/kit/test_drift_workflow.py
create tests/kit/test_metrics.py
create tests/kit/test_metrics_workflow.py
create tests/kit/test_review_context.py
create tests/kit/test_review_report.py
create tests/kit/test_reviewer_definition.py
replace tests/kit/test_reviewers.py
create tests/kit/test_scanner_hygiene.py
replace tests/kit/test_stop_hook.py
replace tests/kit/test_workflow.py
legacy-stamp pyproject.toml [tool.agk]: obsolete after this upgrade; remove it in your own change
template-changed config/protected-paths.txt (kit/templates/protected-paths.txt)
template-line config/protected-paths.txt agk.mk
template-line config/protected-paths.txt agk.toml
template-changed config/reviewers.yaml (kit/templates/reviewers.yaml)
template-changed docs/adr/0001-adopt-agk.md (kit/templates/adr-0001.md)
template-changed pyproject.toml (kit/templates/pyproject.toml)
dry run: 267 files would change; agk.toml would be created with version 0.9.0; nothing was written
Protected classes: `.claude/`, `.github/`, `CLAUDE.md`, `Makefile`, `constitution/`, `scripts/agk/`, `tests/kit/`
The target's check needs an ADR in the same pull request that names each class. Skeleton (write the ADR yourself; the upgrade writes none):
# ADR-NNNN: Upgrade agk from 0.1.0 to 0.9.0
- Status: Proposed
- Date: YYYY-MM-DD
- Deciders: maintainers
- Related: none
- Requirements: REQ-nnn
Protected classes: `.claude/`, `.github/`, `CLAUDE.md`, `Makefile`, `constitution/`, `scripts/agk/`, `tests/kit/`
## Context
## Decision
run: python3 scripts/agk/reviewers.py --codeowners --write
exit 0
```

## Real run, verbatim

```
unchanged .claude/agents/drift-auditor.md
create .claude/agents/reviewer.md
replace .claude/hooks/stop_check.py
replace .claude/settings.json
unchanged .github/PULL_REQUEST_TEMPLATE.md
create .github/workflows/drift-audit.yml
replace .github/workflows/governance.yml
create .github/workflows/metrics.yml
unchanged .gitignore
replace CLAUDE.md
replace Makefile
create agk.mk
create agk.toml
replace constitution/principles.md
unchanged docs/adr/TEMPLATE.md
unchanged docs/briefs/TEMPLATE.md
unchanged docs/specs/TEMPLATE.md
replace scripts/agk/check_adrs.py
unchanged scripts/agk/check_build_state.py
create scripts/agk/check_kit_tests.py
unchanged scripts/agk/check_neutrality.py
unchanged scripts/agk/check_pr_body.py
replace scripts/agk/check_protected_changes.py
replace scripts/agk/check_requirements.py
create scripts/agk/check_review_report.py
create scripts/agk/check_specs.py
replace scripts/agk/common.py
create scripts/agk/config.py
create scripts/agk/doctor.py
create scripts/agk/drift_audit.py
create scripts/agk/metrics.py
create scripts/agk/review_context.py
replace scripts/agk/reviewers.py
replace scripts/agk/traceability.py
replace tests/kit/conftest.py
create tests/kit/drift_fixtures.py
create tests/kit/fixtures/doctor/auto-merge-off/api/repo.json
create tests/kit/fixtures/doctor/auto-merge-off/case.json
create tests/kit/fixtures/doctor/bypass-actor/api/ruleset-1.json
create tests/kit/fixtures/doctor/bypass-actor/case.json
create tests/kit/fixtures/doctor/bypass-on-disabled-ruleset/api/ruleset-2.json
create tests/kit/fixtures/doctor/bypass-on-disabled-ruleset/api/rulesets.json
create tests/kit/fixtures/doctor/bypass-on-disabled-ruleset/case.json
create tests/kit/fixtures/doctor/default-branch-mismatch/case.json
create tests/kit/fixtures/doctor/default-branch-mismatch/tree/agk.toml
create tests/kit/fixtures/doctor/delete-branch-off/api/repo.json
create tests/kit/fixtures/doctor/delete-branch-off/case.json
create tests/kit/fixtures/doctor/disabled-holds-every-rule/api/ruleset-1.json
create tests/kit/fixtures/doctor/disabled-holds-every-rule/api/ruleset-2.json
create tests/kit/fixtures/doctor/disabled-holds-every-rule/api/rulesets.json
create tests/kit/fixtures/doctor/disabled-holds-every-rule/case.json
create tests/kit/fixtures/doctor/drift-disabled/api/workflow-drift-audit.json
create tests/kit/fixtures/doctor/drift-disabled/case.json
create tests/kit/fixtures/doctor/drift-no-schedule/case.json
create tests/kit/fixtures/doctor/drift-no-schedule/tree/.github/workflows/drift-audit.yml
create tests/kit/fixtures/doctor/excluded-default-branch/api/ruleset-1.json
create tests/kit/fixtures/doctor/excluded-default-branch/case.json
create tests/kit/fixtures/doctor/excluded-default-ref/api/ruleset-1.json
create tests/kit/fixtures/doctor/excluded-default-ref/case.json
create tests/kit/fixtures/doctor/merge-commits-allowed/api/ruleset-1.json
create tests/kit/fixtures/doctor/merge-commits-allowed/case.json
create tests/kit/fixtures/doctor/no-admin-empty-list/api/repo.json
create tests/kit/fixtures/doctor/no-admin-empty-list/api/rulesets.json
create tests/kit/fixtures/doctor/no-admin-empty-list/case.json
create tests/kit/fixtures/doctor/no-admin/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-admin/case.json
create tests/kit/fixtures/doctor/no-deletion/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-deletion/case.json
create tests/kit/fixtures/doctor/no-dismiss-stale/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-dismiss-stale/case.json
create tests/kit/fixtures/doctor/no-force-push-block/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-force-push-block/case.json
create tests/kit/fixtures/doctor/no-governance-check/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-governance-check/case.json
create tests/kit/fixtures/doctor/no-linear-history/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-linear-history/case.json
create tests/kit/fixtures/doctor/no-origin-head/case.json
create tests/kit/fixtures/doctor/no-ruleset/api/ruleset-1.json
create tests/kit/fixtures/doctor/no-ruleset/api/rulesets.json
create tests/kit/fixtures/doctor/no-ruleset/case.json
create tests/kit/fixtures/doctor/ok/api/repo.json
create tests/kit/fixtures/doctor/ok/api/ruleset-1.json
create tests/kit/fixtures/doctor/ok/api/rulesets.json
create tests/kit/fixtures/doctor/ok/api/workflow-drift-audit.json
create tests/kit/fixtures/doctor/ok/case.json
create tests/kit/fixtures/doctor/ok/kit/.claude/hooks/x.txt
create tests/kit/fixtures/doctor/ok/kit/kit/manifest.json
create tests/kit/fixtures/doctor/ok/kit/scripts/agk/y.txt
create tests/kit/fixtures/doctor/ok/tree/.claude/hooks/x.txt
create tests/kit/fixtures/doctor/ok/tree/.github/CODEOWNERS
create tests/kit/fixtures/doctor/ok/tree/.github/workflows/drift-audit.yml
create tests/kit/fixtures/doctor/ok/tree/agk.toml
create tests/kit/fixtures/doctor/ok/tree/config/reviewers.yaml
create tests/kit/fixtures/doctor/ok/tree/scripts/agk/y.txt
create tests/kit/fixtures/doctor/placeholder-codeowners/case.json
create tests/kit/fixtures/doctor/placeholder-codeowners/tree/.github/CODEOWNERS
create tests/kit/fixtures/doctor/placeholder-reviewers/case.json
create tests/kit/fixtures/doctor/placeholder-reviewers/tree/config/reviewers.yaml
create tests/kit/fixtures/doctor/stricter-ok/api/ruleset-1.json
create tests/kit/fixtures/doctor/stricter-ok/case.json
create tests/kit/fixtures/doctor/target-all/api/ruleset-1.json
create tests/kit/fixtures/doctor/target-all/case.json
create tests/kit/fixtures/doctor/vendored-edited/case.json
create tests/kit/fixtures/doctor/vendored-edited/tree/.claude/hooks/x.txt
create tests/kit/fixtures/doctor/vendored-missing/case.json
create tests/kit/fixtures/doctor/version-mismatch/case.json
create tests/kit/fixtures/doctor/version-mismatch/tree/agk.toml
create tests/kit/fixtures/doctor/weak-enforcement/api/ruleset-1.json
create tests/kit/fixtures/doctor/weak-enforcement/api/rulesets.json
create tests/kit/fixtures/doctor/weak-enforcement/case.json
create tests/kit/fixtures/doctor/wrong-target/api/ruleset-1.json
create tests/kit/fixtures/doctor/wrong-target/case.json
create tests/kit/fixtures/metrics/cleared-other-commit/checks-0067000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cleared-other-commit/comments-103.json
create tests/kit/fixtures/metrics/cleared-other-commit/commits-103.json
create tests/kit/fixtures/metrics/cleared-other-commit/files-103.json
create tests/kit/fixtures/metrics/cleared-other-commit/jobs-10030.json
create tests/kit/fixtures/metrics/cleared-other-commit/pull-103.json
create tests/kit/fixtures/metrics/cleared-other-commit/pulls.json
create tests/kit/fixtures/metrics/closed-unmerged/checks-0069000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/closed-unmerged/comments-105.json
create tests/kit/fixtures/metrics/closed-unmerged/commits-105.json
create tests/kit/fixtures/metrics/closed-unmerged/files-105.json
create tests/kit/fixtures/metrics/closed-unmerged/jobs-10050.json
create tests/kit/fixtures/metrics/closed-unmerged/pull-105.json
create tests/kit/fixtures/metrics/closed-unmerged/pulls.json
create tests/kit/fixtures/metrics/cost-classes/checks-006f000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cost-classes/checks-0070000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cost-classes/checks-0071000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cost-classes/checks-0072000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cost-classes/checks-0073000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/cost-classes/comments-111.json
create tests/kit/fixtures/metrics/cost-classes/comments-112.json
create tests/kit/fixtures/metrics/cost-classes/comments-113.json
create tests/kit/fixtures/metrics/cost-classes/comments-114.json
create tests/kit/fixtures/metrics/cost-classes/comments-115.json
create tests/kit/fixtures/metrics/cost-classes/commits-111.json
create tests/kit/fixtures/metrics/cost-classes/commits-112.json
create tests/kit/fixtures/metrics/cost-classes/commits-113.json
create tests/kit/fixtures/metrics/cost-classes/commits-114.json
create tests/kit/fixtures/metrics/cost-classes/commits-115.json
create tests/kit/fixtures/metrics/cost-classes/files-111.json
create tests/kit/fixtures/metrics/cost-classes/files-112.json
create tests/kit/fixtures/metrics/cost-classes/files-113.json
create tests/kit/fixtures/metrics/cost-classes/files-114.json
create tests/kit/fixtures/metrics/cost-classes/files-115.json
create tests/kit/fixtures/metrics/cost-classes/jobs-10110.json
create tests/kit/fixtures/metrics/cost-classes/jobs-10120.json
create tests/kit/fixtures/metrics/cost-classes/jobs-10130.json
create tests/kit/fixtures/metrics/cost-classes/jobs-10140.json
create tests/kit/fixtures/metrics/cost-classes/jobs-10150.json
create tests/kit/fixtures/metrics/cost-classes/pull-111.json
create tests/kit/fixtures/metrics/cost-classes/pull-112.json
create tests/kit/fixtures/metrics/cost-classes/pull-113.json
create tests/kit/fixtures/metrics/cost-classes/pull-114.json
create tests/kit/fixtures/metrics/cost-classes/pull-115.json
create tests/kit/fixtures/metrics/cost-classes/pulls.json
create tests/kit/fixtures/metrics/empty-week/pulls.json
create tests/kit/fixtures/metrics/files/checks-0079000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/files/comments-121.json
create tests/kit/fixtures/metrics/files/commits-121.json
create tests/kit/fixtures/metrics/files/files-121.json
create tests/kit/fixtures/metrics/files/jobs-10210.json
create tests/kit/fixtures/metrics/files/pull-121.json
create tests/kit/fixtures/metrics/files/pulls.json
create tests/kit/fixtures/metrics/fix-lists-cleared/checks-0066000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/fix-lists-cleared/checks-006600cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/fix-lists-cleared/checks-006601cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/fix-lists-cleared/comments-102.json
create tests/kit/fixtures/metrics/fix-lists-cleared/commits-102.json
create tests/kit/fixtures/metrics/fix-lists-cleared/files-102.json
create tests/kit/fixtures/metrics/fix-lists-cleared/jobs-10020.json
create tests/kit/fixtures/metrics/fix-lists-cleared/jobs-10021.json
create tests/kit/fixtures/metrics/fix-lists-cleared/jobs-10022.json
create tests/kit/fixtures/metrics/fix-lists-cleared/pull-102.json
create tests/kit/fixtures/metrics/fix-lists-cleared/pulls.json
create tests/kit/fixtures/metrics/governance-split/checks-0083000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/governance-split/checks-008300cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/governance-split/checks-008301cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/governance-split/comments-131.json
create tests/kit/fixtures/metrics/governance-split/commits-131.json
create tests/kit/fixtures/metrics/governance-split/files-131.json
create tests/kit/fixtures/metrics/governance-split/jobs-10310.json
create tests/kit/fixtures/metrics/governance-split/jobs-10311.json
create tests/kit/fixtures/metrics/governance-split/jobs-10312.json
create tests/kit/fixtures/metrics/governance-split/pull-131.json
create tests/kit/fixtures/metrics/governance-split/pulls.json
create tests/kit/fixtures/metrics/governance-unsplit/checks-0084000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/governance-unsplit/checks-008400cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/governance-unsplit/comments-132.json
create tests/kit/fixtures/metrics/governance-unsplit/commits-132.json
create tests/kit/fixtures/metrics/governance-unsplit/files-132.json
create tests/kit/fixtures/metrics/governance-unsplit/jobs-10320.json
create tests/kit/fixtures/metrics/governance-unsplit/jobs-10321.json
create tests/kit/fixtures/metrics/governance-unsplit/pull-132.json
create tests/kit/fixtures/metrics/governance-unsplit/pulls.json
create tests/kit/fixtures/metrics/incomplete/checks-00a1000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/incomplete/comments-161.json
create tests/kit/fixtures/metrics/incomplete/commits-161.json
create tests/kit/fixtures/metrics/incomplete/files-161.json
create tests/kit/fixtures/metrics/incomplete/jobs-10610.json
create tests/kit/fixtures/metrics/incomplete/pull-161.json
create tests/kit/fixtures/metrics/incomplete/pulls.json
create tests/kit/fixtures/metrics/missing-comments/checks-0097000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/missing-comments/commits-151.json
create tests/kit/fixtures/metrics/missing-comments/files-151.json
create tests/kit/fixtures/metrics/missing-comments/jobs-10510.json
create tests/kit/fixtures/metrics/missing-comments/pull-151.json
create tests/kit/fixtures/metrics/missing-comments/pulls.json
create tests/kit/fixtures/metrics/no-verdict-merged/checks-0065000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/no-verdict-merged/checks-006500cccccccccccccccccccccccccccccccccc.json
create tests/kit/fixtures/metrics/no-verdict-merged/comments-101.json
create tests/kit/fixtures/metrics/no-verdict-merged/commits-101.json
create tests/kit/fixtures/metrics/no-verdict-merged/files-101.json
create tests/kit/fixtures/metrics/no-verdict-merged/jobs-10010.json
create tests/kit/fixtures/metrics/no-verdict-merged/jobs-10011.json
create tests/kit/fixtures/metrics/no-verdict-merged/pull-101.json
create tests/kit/fixtures/metrics/no-verdict-merged/pulls.json
create tests/kit/fixtures/metrics/verdict-rejected/checks-0068000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/verdict-rejected/comments-104.json
create tests/kit/fixtures/metrics/verdict-rejected/commits-104.json
create tests/kit/fixtures/metrics/verdict-rejected/files-104.json
create tests/kit/fixtures/metrics/verdict-rejected/jobs-10040.json
create tests/kit/fixtures/metrics/verdict-rejected/pull-104.json
create tests/kit/fixtures/metrics/verdict-rejected/pulls.json
create tests/kit/fixtures/metrics/verdict-suffix/checks-00ab000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/verdict-suffix/comments-171.json
create tests/kit/fixtures/metrics/verdict-suffix/commits-171.json
create tests/kit/fixtures/metrics/verdict-suffix/files-171.json
create tests/kit/fixtures/metrics/verdict-suffix/jobs-10710.json
create tests/kit/fixtures/metrics/verdict-suffix/pull-171.json
create tests/kit/fixtures/metrics/verdict-suffix/pulls.json
create tests/kit/fixtures/metrics/window-edges/checks-008d000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/window-edges/checks-008e000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/window-edges/checks-008f000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/window-edges/checks-0090000000000000000000000000000000000000.json
create tests/kit/fixtures/metrics/window-edges/comments-141.json
create tests/kit/fixtures/metrics/window-edges/comments-142.json
create tests/kit/fixtures/metrics/window-edges/comments-143.json
create tests/kit/fixtures/metrics/window-edges/comments-144.json
create tests/kit/fixtures/metrics/window-edges/commits-141.json
create tests/kit/fixtures/metrics/window-edges/commits-142.json
create tests/kit/fixtures/metrics/window-edges/commits-143.json
create tests/kit/fixtures/metrics/window-edges/commits-144.json
create tests/kit/fixtures/metrics/window-edges/files-141.json
create tests/kit/fixtures/metrics/window-edges/files-142.json
create tests/kit/fixtures/metrics/window-edges/files-143.json
create tests/kit/fixtures/metrics/window-edges/files-144.json
create tests/kit/fixtures/metrics/window-edges/jobs-10410.json
create tests/kit/fixtures/metrics/window-edges/jobs-10420.json
create tests/kit/fixtures/metrics/window-edges/jobs-10430.json
create tests/kit/fixtures/metrics/window-edges/jobs-10440.json
create tests/kit/fixtures/metrics/window-edges/pull-141.json
create tests/kit/fixtures/metrics/window-edges/pull-142.json
create tests/kit/fixtures/metrics/window-edges/pull-143.json
create tests/kit/fixtures/metrics/window-edges/pull-144.json
create tests/kit/fixtures/metrics/window-edges/pulls.json
create tests/kit/pytest.ini
create tests/kit/review_fixtures.py
create tests/kit/test_agk_config.py
create tests/kit/test_agk_mk.py
unchanged tests/kit/test_check_adrs.py
unchanged tests/kit/test_check_build_state.py
create tests/kit/test_check_kit_tests.py
unchanged tests/kit/test_check_neutrality.py
unchanged tests/kit/test_check_pr_body.py
unchanged tests/kit/test_check_protected_changes.py
replace tests/kit/test_check_requirements.py
create tests/kit/test_check_specs.py
create tests/kit/test_doctor.py
create tests/kit/test_drift_audit.py
create tests/kit/test_drift_workflow.py
create tests/kit/test_metrics.py
create tests/kit/test_metrics_workflow.py
create tests/kit/test_review_context.py
create tests/kit/test_review_report.py
create tests/kit/test_reviewer_definition.py
replace tests/kit/test_reviewers.py
create tests/kit/test_scanner_hygiene.py
replace tests/kit/test_stop_hook.py
replace tests/kit/test_workflow.py
legacy-stamp pyproject.toml [tool.agk]: obsolete after this upgrade; remove it in your own change
template-changed config/protected-paths.txt (kit/templates/protected-paths.txt)
template-line config/protected-paths.txt agk.mk
template-line config/protected-paths.txt agk.toml
template-changed config/reviewers.yaml (kit/templates/reviewers.yaml)
template-changed docs/adr/0001-adopt-agk.md (kit/templates/adr-0001.md)
template-changed pyproject.toml (kit/templates/pyproject.toml)
upgraded 267 files; agk.toml is created with version 0.9.0
Protected classes: `.claude/`, `.github/`, `CLAUDE.md`, `Makefile`, `constitution/`, `scripts/agk/`, `tests/kit/`
The target's check needs an ADR in the same pull request that names each class. Skeleton (write the ADR yourself; the upgrade writes none):
# ADR-NNNN: Upgrade agk from 0.1.0 to 0.9.0
- Status: Proposed
- Date: YYYY-MM-DD
- Deciders: maintainers
- Related: none
- Requirements: REQ-nnn
Protected classes: `.claude/`, `.github/`, `CLAUDE.md`, `Makefile`, `constitution/`, `scripts/agk/`, `tests/kit/`
## Context
## Decision
run: python3 scripts/agk/reviewers.py --codeowners --write
exit 0
```

Second run of the real command (`python3 scripts/agk/upgrade.py /home/user/agk-sandbox`): last line `nothing to do`, exit 0, no file touched.

## Zero-touch check

`git ls-files -s` before (46 entries) and after `git add -A` (297 entries): removed 0; mode changes 0.

Changed (18 entries whose blob changed):

```
.claude/hooks/stop_check.py
.claude/settings.json
.github/CODEOWNERS
.github/workflows/governance.yml
CLAUDE.md
Makefile
constitution/principles.md
scripts/agk/check_adrs.py
scripts/agk/check_protected_changes.py
scripts/agk/check_requirements.py
scripts/agk/common.py
scripts/agk/reviewers.py
scripts/agk/traceability.py
tests/kit/conftest.py
tests/kit/test_check_requirements.py
tests/kit/test_reviewers.py
tests/kit/test_stop_hook.py
tests/kit/test_workflow.py
```

Unchanged (28 of the 46 tracked files, including every product file):

```
.claude/agents/drift-auditor.md
.github/PULL_REQUEST_TEMPLATE.md
.gitignore
README.md
config/neutrality.txt
config/protected-paths.txt
config/reviewers.yaml
constitution/vision.md
docs/adr/0001-adopt-agk.md
docs/adr/0002-wordcount.md
docs/adr/TEMPLATE.md
docs/briefs/TEMPLATE.md
docs/build-state.md
docs/requirements.md
docs/runs/decisions-log.md
docs/runs/sandbox-day-1.md
docs/specs/TEMPLATE.md
pyproject.toml
scripts/agk/check_build_state.py
scripts/agk/check_neutrality.py
scripts/agk/check_pr_body.py
src/wordcount.py
tests/kit/test_check_adrs.py
tests/kit/test_check_build_state.py
tests/kit/test_check_neutrality.py
tests/kit/test_check_pr_body.py
tests/kit/test_check_protected_changes.py
tests/test_wordcount.py
```

Added (251 entries: the 250 `create` lines of the real run, which include `agk.toml`, and the sandbox's ADR-0003):

```
.claude/agents/reviewer.md
.github/workflows/drift-audit.yml
.github/workflows/metrics.yml
agk.mk
agk.toml
docs/adr/0003-upgrade-kit-0-1-0-to-0-9-0.md
scripts/agk/check_kit_tests.py
scripts/agk/check_review_report.py
scripts/agk/check_specs.py
scripts/agk/config.py
scripts/agk/doctor.py
scripts/agk/drift_audit.py
scripts/agk/metrics.py
scripts/agk/review_context.py
tests/kit/drift_fixtures.py
tests/kit/fixtures/doctor/auto-merge-off/api/repo.json
tests/kit/fixtures/doctor/auto-merge-off/case.json
tests/kit/fixtures/doctor/bypass-actor/api/ruleset-1.json
tests/kit/fixtures/doctor/bypass-actor/case.json
tests/kit/fixtures/doctor/bypass-on-disabled-ruleset/api/ruleset-2.json
tests/kit/fixtures/doctor/bypass-on-disabled-ruleset/api/rulesets.json
tests/kit/fixtures/doctor/bypass-on-disabled-ruleset/case.json
tests/kit/fixtures/doctor/default-branch-mismatch/case.json
tests/kit/fixtures/doctor/default-branch-mismatch/tree/agk.toml
tests/kit/fixtures/doctor/delete-branch-off/api/repo.json
tests/kit/fixtures/doctor/delete-branch-off/case.json
tests/kit/fixtures/doctor/disabled-holds-every-rule/api/ruleset-1.json
tests/kit/fixtures/doctor/disabled-holds-every-rule/api/ruleset-2.json
tests/kit/fixtures/doctor/disabled-holds-every-rule/api/rulesets.json
tests/kit/fixtures/doctor/disabled-holds-every-rule/case.json
tests/kit/fixtures/doctor/drift-disabled/api/workflow-drift-audit.json
tests/kit/fixtures/doctor/drift-disabled/case.json
tests/kit/fixtures/doctor/drift-no-schedule/case.json
tests/kit/fixtures/doctor/drift-no-schedule/tree/.github/workflows/drift-audit.yml
tests/kit/fixtures/doctor/excluded-default-branch/api/ruleset-1.json
tests/kit/fixtures/doctor/excluded-default-branch/case.json
tests/kit/fixtures/doctor/excluded-default-ref/api/ruleset-1.json
tests/kit/fixtures/doctor/excluded-default-ref/case.json
tests/kit/fixtures/doctor/merge-commits-allowed/api/ruleset-1.json
tests/kit/fixtures/doctor/merge-commits-allowed/case.json
tests/kit/fixtures/doctor/no-admin-empty-list/api/repo.json
tests/kit/fixtures/doctor/no-admin-empty-list/api/rulesets.json
tests/kit/fixtures/doctor/no-admin-empty-list/case.json
tests/kit/fixtures/doctor/no-admin/api/ruleset-1.json
tests/kit/fixtures/doctor/no-admin/case.json
tests/kit/fixtures/doctor/no-deletion/api/ruleset-1.json
tests/kit/fixtures/doctor/no-deletion/case.json
tests/kit/fixtures/doctor/no-dismiss-stale/api/ruleset-1.json
tests/kit/fixtures/doctor/no-dismiss-stale/case.json
tests/kit/fixtures/doctor/no-force-push-block/api/ruleset-1.json
tests/kit/fixtures/doctor/no-force-push-block/case.json
tests/kit/fixtures/doctor/no-governance-check/api/ruleset-1.json
tests/kit/fixtures/doctor/no-governance-check/case.json
tests/kit/fixtures/doctor/no-linear-history/api/ruleset-1.json
tests/kit/fixtures/doctor/no-linear-history/case.json
tests/kit/fixtures/doctor/no-origin-head/case.json
tests/kit/fixtures/doctor/no-ruleset/api/ruleset-1.json
tests/kit/fixtures/doctor/no-ruleset/api/rulesets.json
tests/kit/fixtures/doctor/no-ruleset/case.json
tests/kit/fixtures/doctor/ok/api/repo.json
tests/kit/fixtures/doctor/ok/api/ruleset-1.json
tests/kit/fixtures/doctor/ok/api/rulesets.json
tests/kit/fixtures/doctor/ok/api/workflow-drift-audit.json
tests/kit/fixtures/doctor/ok/case.json
tests/kit/fixtures/doctor/ok/kit/.claude/hooks/x.txt
tests/kit/fixtures/doctor/ok/kit/kit/manifest.json
tests/kit/fixtures/doctor/ok/kit/scripts/agk/y.txt
tests/kit/fixtures/doctor/ok/tree/.claude/hooks/x.txt
tests/kit/fixtures/doctor/ok/tree/.github/CODEOWNERS
tests/kit/fixtures/doctor/ok/tree/.github/workflows/drift-audit.yml
tests/kit/fixtures/doctor/ok/tree/agk.toml
tests/kit/fixtures/doctor/ok/tree/config/reviewers.yaml
tests/kit/fixtures/doctor/ok/tree/scripts/agk/y.txt
tests/kit/fixtures/doctor/placeholder-codeowners/case.json
tests/kit/fixtures/doctor/placeholder-codeowners/tree/.github/CODEOWNERS
tests/kit/fixtures/doctor/placeholder-reviewers/case.json
tests/kit/fixtures/doctor/placeholder-reviewers/tree/config/reviewers.yaml
tests/kit/fixtures/doctor/stricter-ok/api/ruleset-1.json
tests/kit/fixtures/doctor/stricter-ok/case.json
tests/kit/fixtures/doctor/target-all/api/ruleset-1.json
tests/kit/fixtures/doctor/target-all/case.json
tests/kit/fixtures/doctor/vendored-edited/case.json
tests/kit/fixtures/doctor/vendored-edited/tree/.claude/hooks/x.txt
tests/kit/fixtures/doctor/vendored-missing/case.json
tests/kit/fixtures/doctor/version-mismatch/case.json
tests/kit/fixtures/doctor/version-mismatch/tree/agk.toml
tests/kit/fixtures/doctor/weak-enforcement/api/ruleset-1.json
tests/kit/fixtures/doctor/weak-enforcement/api/rulesets.json
tests/kit/fixtures/doctor/weak-enforcement/case.json
tests/kit/fixtures/doctor/wrong-target/api/ruleset-1.json
tests/kit/fixtures/doctor/wrong-target/case.json
tests/kit/fixtures/metrics/cleared-other-commit/checks-0067000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/cleared-other-commit/comments-103.json
tests/kit/fixtures/metrics/cleared-other-commit/commits-103.json
tests/kit/fixtures/metrics/cleared-other-commit/files-103.json
tests/kit/fixtures/metrics/cleared-other-commit/jobs-10030.json
tests/kit/fixtures/metrics/cleared-other-commit/pull-103.json
tests/kit/fixtures/metrics/cleared-other-commit/pulls.json
tests/kit/fixtures/metrics/closed-unmerged/checks-0069000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/closed-unmerged/comments-105.json
tests/kit/fixtures/metrics/closed-unmerged/commits-105.json
tests/kit/fixtures/metrics/closed-unmerged/files-105.json
tests/kit/fixtures/metrics/closed-unmerged/jobs-10050.json
tests/kit/fixtures/metrics/closed-unmerged/pull-105.json
tests/kit/fixtures/metrics/closed-unmerged/pulls.json
tests/kit/fixtures/metrics/cost-classes/checks-006f000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/cost-classes/checks-0070000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/cost-classes/checks-0071000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/cost-classes/checks-0072000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/cost-classes/checks-0073000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/cost-classes/comments-111.json
tests/kit/fixtures/metrics/cost-classes/comments-112.json
tests/kit/fixtures/metrics/cost-classes/comments-113.json
tests/kit/fixtures/metrics/cost-classes/comments-114.json
tests/kit/fixtures/metrics/cost-classes/comments-115.json
tests/kit/fixtures/metrics/cost-classes/commits-111.json
tests/kit/fixtures/metrics/cost-classes/commits-112.json
tests/kit/fixtures/metrics/cost-classes/commits-113.json
tests/kit/fixtures/metrics/cost-classes/commits-114.json
tests/kit/fixtures/metrics/cost-classes/commits-115.json
tests/kit/fixtures/metrics/cost-classes/files-111.json
tests/kit/fixtures/metrics/cost-classes/files-112.json
tests/kit/fixtures/metrics/cost-classes/files-113.json
tests/kit/fixtures/metrics/cost-classes/files-114.json
tests/kit/fixtures/metrics/cost-classes/files-115.json
tests/kit/fixtures/metrics/cost-classes/jobs-10110.json
tests/kit/fixtures/metrics/cost-classes/jobs-10120.json
tests/kit/fixtures/metrics/cost-classes/jobs-10130.json
tests/kit/fixtures/metrics/cost-classes/jobs-10140.json
tests/kit/fixtures/metrics/cost-classes/jobs-10150.json
tests/kit/fixtures/metrics/cost-classes/pull-111.json
tests/kit/fixtures/metrics/cost-classes/pull-112.json
tests/kit/fixtures/metrics/cost-classes/pull-113.json
tests/kit/fixtures/metrics/cost-classes/pull-114.json
tests/kit/fixtures/metrics/cost-classes/pull-115.json
tests/kit/fixtures/metrics/cost-classes/pulls.json
tests/kit/fixtures/metrics/empty-week/pulls.json
tests/kit/fixtures/metrics/files/checks-0079000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/files/comments-121.json
tests/kit/fixtures/metrics/files/commits-121.json
tests/kit/fixtures/metrics/files/files-121.json
tests/kit/fixtures/metrics/files/jobs-10210.json
tests/kit/fixtures/metrics/files/pull-121.json
tests/kit/fixtures/metrics/files/pulls.json
tests/kit/fixtures/metrics/fix-lists-cleared/checks-0066000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/fix-lists-cleared/checks-006600cccccccccccccccccccccccccccccccccc.json
tests/kit/fixtures/metrics/fix-lists-cleared/checks-006601cccccccccccccccccccccccccccccccccc.json
tests/kit/fixtures/metrics/fix-lists-cleared/comments-102.json
tests/kit/fixtures/metrics/fix-lists-cleared/commits-102.json
tests/kit/fixtures/metrics/fix-lists-cleared/files-102.json
tests/kit/fixtures/metrics/fix-lists-cleared/jobs-10020.json
tests/kit/fixtures/metrics/fix-lists-cleared/jobs-10021.json
tests/kit/fixtures/metrics/fix-lists-cleared/jobs-10022.json
tests/kit/fixtures/metrics/fix-lists-cleared/pull-102.json
tests/kit/fixtures/metrics/fix-lists-cleared/pulls.json
tests/kit/fixtures/metrics/governance-split/checks-0083000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/governance-split/checks-008300cccccccccccccccccccccccccccccccccc.json
tests/kit/fixtures/metrics/governance-split/checks-008301cccccccccccccccccccccccccccccccccc.json
tests/kit/fixtures/metrics/governance-split/comments-131.json
tests/kit/fixtures/metrics/governance-split/commits-131.json
tests/kit/fixtures/metrics/governance-split/files-131.json
tests/kit/fixtures/metrics/governance-split/jobs-10310.json
tests/kit/fixtures/metrics/governance-split/jobs-10311.json
tests/kit/fixtures/metrics/governance-split/jobs-10312.json
tests/kit/fixtures/metrics/governance-split/pull-131.json
tests/kit/fixtures/metrics/governance-split/pulls.json
tests/kit/fixtures/metrics/governance-unsplit/checks-0084000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/governance-unsplit/checks-008400cccccccccccccccccccccccccccccccccc.json
tests/kit/fixtures/metrics/governance-unsplit/comments-132.json
tests/kit/fixtures/metrics/governance-unsplit/commits-132.json
tests/kit/fixtures/metrics/governance-unsplit/files-132.json
tests/kit/fixtures/metrics/governance-unsplit/jobs-10320.json
tests/kit/fixtures/metrics/governance-unsplit/jobs-10321.json
tests/kit/fixtures/metrics/governance-unsplit/pull-132.json
tests/kit/fixtures/metrics/governance-unsplit/pulls.json
tests/kit/fixtures/metrics/incomplete/checks-00a1000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/incomplete/comments-161.json
tests/kit/fixtures/metrics/incomplete/commits-161.json
tests/kit/fixtures/metrics/incomplete/files-161.json
tests/kit/fixtures/metrics/incomplete/jobs-10610.json
tests/kit/fixtures/metrics/incomplete/pull-161.json
tests/kit/fixtures/metrics/incomplete/pulls.json
tests/kit/fixtures/metrics/missing-comments/checks-0097000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/missing-comments/commits-151.json
tests/kit/fixtures/metrics/missing-comments/files-151.json
tests/kit/fixtures/metrics/missing-comments/jobs-10510.json
tests/kit/fixtures/metrics/missing-comments/pull-151.json
tests/kit/fixtures/metrics/missing-comments/pulls.json
tests/kit/fixtures/metrics/no-verdict-merged/checks-0065000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/no-verdict-merged/checks-006500cccccccccccccccccccccccccccccccccc.json
tests/kit/fixtures/metrics/no-verdict-merged/comments-101.json
tests/kit/fixtures/metrics/no-verdict-merged/commits-101.json
tests/kit/fixtures/metrics/no-verdict-merged/files-101.json
tests/kit/fixtures/metrics/no-verdict-merged/jobs-10010.json
tests/kit/fixtures/metrics/no-verdict-merged/jobs-10011.json
tests/kit/fixtures/metrics/no-verdict-merged/pull-101.json
tests/kit/fixtures/metrics/no-verdict-merged/pulls.json
tests/kit/fixtures/metrics/verdict-rejected/checks-0068000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/verdict-rejected/comments-104.json
tests/kit/fixtures/metrics/verdict-rejected/commits-104.json
tests/kit/fixtures/metrics/verdict-rejected/files-104.json
tests/kit/fixtures/metrics/verdict-rejected/jobs-10040.json
tests/kit/fixtures/metrics/verdict-rejected/pull-104.json
tests/kit/fixtures/metrics/verdict-rejected/pulls.json
tests/kit/fixtures/metrics/verdict-suffix/checks-00ab000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/verdict-suffix/comments-171.json
tests/kit/fixtures/metrics/verdict-suffix/commits-171.json
tests/kit/fixtures/metrics/verdict-suffix/files-171.json
tests/kit/fixtures/metrics/verdict-suffix/jobs-10710.json
tests/kit/fixtures/metrics/verdict-suffix/pull-171.json
tests/kit/fixtures/metrics/verdict-suffix/pulls.json
tests/kit/fixtures/metrics/window-edges/checks-008d000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/window-edges/checks-008e000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/window-edges/checks-008f000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/window-edges/checks-0090000000000000000000000000000000000000.json
tests/kit/fixtures/metrics/window-edges/comments-141.json
tests/kit/fixtures/metrics/window-edges/comments-142.json
tests/kit/fixtures/metrics/window-edges/comments-143.json
tests/kit/fixtures/metrics/window-edges/comments-144.json
tests/kit/fixtures/metrics/window-edges/commits-141.json
tests/kit/fixtures/metrics/window-edges/commits-142.json
tests/kit/fixtures/metrics/window-edges/commits-143.json
tests/kit/fixtures/metrics/window-edges/commits-144.json
tests/kit/fixtures/metrics/window-edges/files-141.json
tests/kit/fixtures/metrics/window-edges/files-142.json
tests/kit/fixtures/metrics/window-edges/files-143.json
tests/kit/fixtures/metrics/window-edges/files-144.json
tests/kit/fixtures/metrics/window-edges/jobs-10410.json
tests/kit/fixtures/metrics/window-edges/jobs-10420.json
tests/kit/fixtures/metrics/window-edges/jobs-10430.json
tests/kit/fixtures/metrics/window-edges/jobs-10440.json
tests/kit/fixtures/metrics/window-edges/pull-141.json
tests/kit/fixtures/metrics/window-edges/pull-142.json
tests/kit/fixtures/metrics/window-edges/pull-143.json
tests/kit/fixtures/metrics/window-edges/pull-144.json
tests/kit/fixtures/metrics/window-edges/pulls.json
tests/kit/pytest.ini
tests/kit/review_fixtures.py
tests/kit/test_agk_config.py
tests/kit/test_agk_mk.py
tests/kit/test_check_kit_tests.py
tests/kit/test_check_specs.py
tests/kit/test_doctor.py
tests/kit/test_drift_audit.py
tests/kit/test_drift_workflow.py
tests/kit/test_metrics.py
tests/kit/test_metrics_workflow.py
tests/kit/test_review_context.py
tests/kit/test_review_report.py
tests/kit/test_reviewer_definition.py
tests/kit/test_scanner_hygiene.py
```

`pyproject.toml` is not in the changed list: it is byte for byte the same, and its `[tool.agk]` table is obsolete (the upgrade printed
`legacy-stamp pyproject.toml [tool.agk]: obsolete after this upgrade; remove it in your own change`).

## The ADR

`docs/adr/0003-upgrade-kit-0-1-0-to-0-9-0.md` in the sandbox (Status Proposed, dated 2026-10-16 from `date -u`, `Requirements: REQ-001`),
with the printed line

```
Protected classes: `.claude/`, `.github/`, `CLAUDE.md`, `Makefile`, `constitution/`, `scripts/agk/`, `tests/kit/`
```

and the decision "Upgrade the kit from 0.1.0 to 0.9.0".

## `make governance` in the sandbox

First run, after the upgrade and the ADR (verbatim):

```
python3 scripts/agk/check_protected_changes.py
ok protected-changes (protected change covered by an ADR)
python3 scripts/agk/check_requirements.py
ok requirements (5 requirements)
python3 scripts/agk/check_adrs.py
ok adrs (3 ADRs)
python3 scripts/agk/check_specs.py
ok specs
python3 scripts/agk/check_neutrality.py
ok neutrality (0 tokens)
python3 scripts/agk/check_build_state.py
ok build-state
python3 scripts/agk/check_kit_tests.py
ok kit-tests (no kit/manifest.json here; nothing to check)
python3 scripts/agk/reviewers.py --check
ok reviewers
python3 scripts/agk/reviewers.py --check-codeowners
FAIL reviewers: .github/CODEOWNERS differs from the rendering of config/reviewers.yaml; re-render it
make: *** [agk.mk:17: agk-governance] Error 1
exit 2
```

The printed step `python3 scripts/agk/reviewers.py --codeowners --write` was then run (`wrote .github/CODEOWNERS`); it removed the duplicate
lines (`/Makefile`, `/pyproject.toml`, `/tests/kit/`, `/scripts/agk/` each appeared twice in the 0.1.0 rendering). Run on the final commit
(verbatim):

```
python3 scripts/agk/check_protected_changes.py
ok protected-changes (protected change covered by an ADR)
python3 scripts/agk/check_requirements.py
ok requirements (5 requirements)
python3 scripts/agk/check_adrs.py
ok adrs (3 ADRs)
python3 scripts/agk/check_specs.py
ok specs
python3 scripts/agk/check_neutrality.py
ok neutrality (0 tokens)
python3 scripts/agk/check_build_state.py
ok build-state
python3 scripts/agk/check_kit_tests.py
ok kit-tests (no kit/manifest.json here; nothing to check)
python3 scripts/agk/reviewers.py --check
ok reviewers
python3 scripts/agk/reviewers.py --check-codeowners
ok reviewers (.github/CODEOWNERS matches)
exit 0
```

Also in the sandbox, on the same tree: `make lint`: `All checks passed!` (exit 0); `make test`: `467 passed, 2 skipped` for the kit tests, then
`3 passed` for the project tests (exit 0).

## Observations for the maintainers

1. **CODEOWNERS.** The 0.1.0 CODEOWNERS is a rendering with duplicate lines, so `--check-codeowners` of the 0.9.0 kit fails on it until it is
   re-rendered. The upgrade prints the command (rule 12) but cannot know that the file differs; the run above shows the failure and the fix.
2. **Protected list.** The sandbox's `config/protected-paths.txt` does not have `agk.mk` and `agk.toml`, which the 0.9.0 template has; they are
   unprotected in the sandbox until a separate change adds them (the upgrade printed `template-line` for both). The same holds for the
   other `template-changed` lines (`config/reviewers.yaml`, `docs/adr/0001-adopt-agk.md`, `pyproject.toml`): user-owned, not rewritten.
3. **Pull request checks.** The pull request's own `governance` run on GitHub was not polled (rule: never poll CI). The local runs above are
   the evidence available to the agent.
4. **Criterion c** is met when the maintainers have reviewed and merged the sandbox pull request and the `governance` check of that
   pull request is green; the agent did not merge or approve anything.

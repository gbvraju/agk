# ADR-0868: Plan publish runs no command in its brief check; the project source search is left out there

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers
- Related: ADR-0857, ADR-0756, ADR-0850, SPEC-0043, SPEC-0046, REQ-037, REQ-050, brief #2086, brief #2065
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The default branch went red on 76b45be2 (governance job 140839534103, `1 failed, 19437 passed`):
`tests/kit/test_plan_publish.py::test_ac2_rule_25_publish_runs_no_command` fails with `publish runs no command`.
SPEC-0043 rule 25 has `plan_intake.py publish` print its `gh api` commands and run none; the test holds that publish
starts no process at all. Publish refuses a brief that `check_brief.brief_result` fails (ADR-0756), and #2079
(brief #2065, ADR-0857 answer 2) added a project's source search to that check's study, which lists the tracked files
with `gates/pins.py` `tracked`, a `git ls-files` process.

## Decision

1. `brief_study.project_matches`, `brief_study.study_result` and `check_brief.brief_result` take `commands`, true by
   default. With it false, `project_matches` does not read the project's source (`project_source`, the git listing)
   and adds one line `not run code search: the caller runs no command (SPEC-0043 rule 25)`; the kit's scripts, the
   kit's reference guide and the parts are still searched, as files only.
2. `plan_intake.brief_check`, the brief check of `publish`, passes `commands=False`. Every other caller keeps the
   default and the search of ADR-0857 is unchanged.
3. The check of rule 25 is not changed: the test still refuses every `subprocess` call and `os.system`.

## Consequences

Publish runs no command again and main turns green. Publish no longer warns that a brief leaves out a project source
match; those warnings are warnings only (ADR-0857 answer 3) and `check_brief.py --root .`, which the person runs on the
rendered briefs before publish, still gives them. Two tests in `tests/kit/test_brief_existing_project.py` hold the
option.

## Residual

- 2026-11-28: `Q-2086-1`: whether publish should instead read the source by a walk of the files (the no-git branch of
  `pins.tracked`), which keeps the warning but reads untracked files. Left out as the narrower change.

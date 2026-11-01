# Proposed spec amendments 107 (SPEC-0001; REQ-016, REQ-039)

Date: 2026-11-01 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for ADR-0242
(brief #453), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0001-agk-init.md`. The number 107 is
the one the brief names. It needs a person's `Approve: SPEC-0001`; no session posts it. It records in the spec what
`agk-project-test` does once brief #453 merges; with the default `pr_tests = "full"`, or without a `[testing]` table, the
target behaves exactly as the sentence says today.

1. **SPEC-0001 rule 18, tests directories**, the sentence "`agk-project-test` runs the `project_tests` command of `agk.toml`"
   gains, after "treating pytest exit 5, nothing collected, as success)": "; it does so through `scripts/agk/project_tests.py`,
   and with `[testing] pr_tests = "selected"` (brief #453, ADR-0242) a `pull_request` event, passed by the workflow as `EVENT`,
   runs only the regression set that `prepush.py` builds for the head against its merge base (the whole command when the plan
   is full or a selected file lies in no `[proof]` area), while a push, any other or unknown event, and a release pull request
   (one that changes `version` in `agk.toml` against its base) run the whole command; before anything runs it prints, and adds
   to the job summary, the plan's regression section and what is not run and why. `pr_tests` is `full` by default, and any
   other value than `full` or `selected` is refused naming the setting."
2. **SPEC-0001 rule 18**, the sentence "A test added under `tests/` in a target is collected and run by `make test` and by the
   CI step `agk-project-test`; a failing one makes both fail." gains at its end: "With `pr_tests = "selected"` the CI step of a
   pull request runs such a test only when the change selects it; the default branch and a release pull request always run it."
   The cases are those of `tests/kit/test_project_test_selection.py`.

# ADR-0242: a pull request's CI can run only the selected tests, while the default branch and every release run the full suite (REQ-016, REQ-039, brief 453)

- Status: Proposed
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0220, ADR-0227, ADR-0238
- Requirements: REQ-016, REQ-039

Protected classes: `agk.mk`, `.github/` (`.github/workflows/governance.yml`), `scripts/agk/`, `tests/kit/`, `kit/`

## Context

Governance runs `project_tests` in full on every push to a pull request (`make -f agk.mk agk-project-test`), the largest share
of a project's minutes in the pilot (#287's table; #289 parts 2 and 4). The person decided on 2026-11-01 (the field note on
#453) that pull requests may run the selected tests, while the full suite stays on the default branch and before every
release. The router already turns a red default branch into a priority-0 brief (SPEC-0032 rule 7), so the backstop exists
while the default branch runs in full. The regression selection of `impact.py` (brief #373) and the regression sets of
`prepush.py` (brief #417) already say what a change needs; brief #453 gives the answers.

## Decision

1. **The setting (answer 1).** The `[testing]` table accepts `pr_tests`, `full` (the default) or `selected`. It joins
   `impact.KEYS`; `impact.testing_table` refuses any other value with `(setting: pr_tests)`, never the value, and
   `impact.pr_tests(root)` reads it: `full` without the table or the key. With `full`, or with no `[testing]` table, the
   step runs the `project_tests` command exactly as before and prints nothing more.
2. **The script (answer 2).** `agk-project-test` calls a new installed script, `scripts/agk/project_tests.py`, listed in
   `kit/manifest.json` (verbatim). It keeps the notice of an empty `project_tests` word for word, makes no network call
   and reuses `prepush.regression_sets`, `impact.impact` and `impact.text` rather than copying them. With `selected` it decides by the event, which the workflow passes in as `EVENT: ${{ github.event_name }}`, as the
   `Secret scan` step does. On `pull_request` it runs the regression set of the head against its merge base with the base
   (`AGK_BASE`, set by the step `Base of the merge ref`): the full `project_tests` command when the plan is full (an
   `always_full` path, `thorough`, unmapped files under `balanced`), else each selected run in its `[proof]` area's folder
   with that area's command. On `push`, on any other event, or when `EVENT` is unset, it runs the full command.
3. **Release (answer 3).** A pull request whose `agk.toml` `version` differs from the base's, read with
   `check_release.toml_version` reads it (Q-453-7), runs the full command (`project tests: full (release: version raised in agk.toml)`).
4. **What is said (answer 4).** Under `selected`, before anything runs, the step prints
   `project tests: pr_tests selected, event <event>`, then the plan's `regression` section and the lines of what is not run
   and why, then the decision (`project tests: full (<why>)` or one line per selected run), and appends the same lines to
   `$GITHUB_STEP_SUMMARY` when it is set. Each run ends with `project tests: <name> ok|FAIL (<s>s): <reason>`; the first
   failure ends the step with exit 1.
5. **The kit (answer 5).** The kit's repository is unchanged: its `Project tests` step is skipped (`kit/agk-kit.mk`) and its
   `agk.toml` does not set `pr_tests`.
6. **Guides and templates (answer 6).** `docs/guides/project-ci.md` gains "Selected tests on pull requests"; both `agk.toml`
   templates list `# pr_tests = "full"` in the commented `[testing]` table; `docs/guides/testing.md` names the key.
7. **The spec (answer 7).** `docs/runs/proposed-spec-amendments-107.md` proposes the change to SPEC-0001 rule 18's
   `agk-project-test` sentence. It is a proposal only; no rule in a spec changes.
8. **Tests first (answer 8).** `tests/kit/test_project_test_selection.py`, with an invented project in a temporary git
   repository whose commands only record what they ran.

## Consequences

A project that sets `pr_tests = "selected"`, by a pull request with an ADR since `agk.toml` is protected, spends the full
suite's minutes only on the default branch and on release pull requests; a pull request runs what its change selects. A
neighbour the map does not cover can break and be found only on the default branch, where the router opens a priority-0
brief. Stepping back is `pr_tests = "full"`. Nothing changes for a project that leaves the setting out, and this repository
leaves it out.

## Residual

- 2026-11-01: Q-453-1: a bad `[testing]` table makes the step fail with its refusal and run nothing, as the test plan, the
  pre-push gate and proof refuse it; the step is red, never silently skipped.
- 2026-11-01: Q-453-2: a selected file that lies in no `[proof]` area, which `prepush.py` lists as not run, makes the step run
  the full command under `selected`, so a selected test is never dropped in CI (the conservative reading).
- 2026-11-01: Q-453-3: any change of `version` against the base (raised, lowered, added or removed) counts as a release and runs
  the full command; the brief names raising, and the conservative reading runs more.
- 2026-11-01: Q-453-4: when the base or the merge base does not resolve on a `pull_request` event, the step runs the full
  command and says why (`project tests: full (the base does not resolve)`).
- 2026-11-01: Q-453-5: the selected runs have no timeout of their own, as the full command had none; the job's limit applies.
  `proof_timeout` stays proof's.
- 2026-11-01: Q-453-6: the kit has no script that writes `kit/manifest.json`; the one line is added in sorted order, as the
  pull request of brief #441 did, and `kit_hashes.py` checks it.
- 2026-11-01: Q-453-7: `check_release.py` is kit-only and never installed, so the installed script cannot import it;
  `project_tests.toml_version` restates its reading of `version` (stdlib `tomllib`), and a kit test pins the two equal on the
  same texts, as `new_spec.py` restates a common rule (Q-K4-216). `prepush.py`, which the script imports, imports `socket` only
  for the lock owner's host name; nothing here opens a connection.
- 2026-11-01: Q-453-8: three existing tests pinned the old recipe of `agk-project-test` and the old `Project tests` step
  (`tests/kit/test_workflow.py`, `tests/kit_dev/test_init.py`, `tests/kit_dev/test_make_once.py`); they now pin the new recipe
  and the `env:` block, and assert the same order and the same outcomes as before.

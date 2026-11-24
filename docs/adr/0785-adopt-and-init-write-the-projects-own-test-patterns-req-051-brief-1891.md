# ADR-0785: Adopt and init write the project's own test patterns (REQ-051, REQ-010)

- Status: Accepted
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1891, ADR-0490 (front-end test folders in `test_dirs`), ADR-0769 (the Windows forms of `test_dirs`),
  ADR-0008 (adopt and its detection of tests), ADR-0514 (installed scripts import only installed modules), ADR-0371
  (the stack table of `config/stack-signals.toml`), amendment 231, plan #661
- Requirements: REQ-051, REQ-010

Protected classes: `agk.toml`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

The adopt test run AD-04 (comment 7120904046 on #1771) adopted a Node and TypeScript project whose one test was
`tests/price.test.js`. `adopt.py` wrote `test_patterns = ["test_*.py"]`, so `test_plan.py` selected nothing when that
test changed. Reproduced on main: `adopt.detect_tests` gives `(['tests'], ['test_*.py'])`, and
`impact.is_test_file("tests/price.test.js", ["tests"], ["test_*.py"])` is `False`. The detector matched only the two
Python names and four TypeScript names (SPEC-0044 rule 10), and fell back to the Python default for every other tree.
`survey._test_language` already knows the six web extensions. `init.py` wrote no `test_patterns` at all. The owner's
word (2026-11-24, the steward chat, quoted as data): "Yes, draft the test briefs and post the runs".

## Decision

1. `tree_walk.FRONTEND_PATTERNS` (installed; `doctor.py` reads it unchanged) is `*.test.<ext>` and `*.spec.<ext>` over
   `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts` and `.tsx` (`tree_walk.WEB_EXTENSIONS`): twelve patterns, the jest and vitest
   names (verify). `.mts` and `.cts` are not added (`Q-AN-5`).
2. `adopt.scan_tests` (`detect_tests` returns its folders and patterns) matches file names with `fnmatch.fnmatchcase`,
   as `impact.is_test_file` does, so `Cart.Test.js` is not detected on any system. It keeps the topmost folders found
   and every pattern matched, sorted. Python-only output is unchanged.
3. With no test file found, the stacks whose manifests of the kit's own `config/stack-signals.toml` the tree holds,
   outside the skipped folders and the table's `ignore` folders, give the patterns: a Python manifest
   `["test_*.py"]` (`Q-AN-2`), `package.json` the twelve web patterns, both give both, and neither gives
   `test_patterns = []` with `test_dirs = ["tests"]`. Adopt then prints that `test_patterns` is empty, naming the setting.
4. `init.py` writes `test_patterns = [...]` after its `test_dirs` line, and prints it, when a test file or a manifest is
   found and the patterns are not all Python names; an empty tree, or one whose patterns are all Python names
   (`test_*.py`, `*_test.py` or both), renders the template byte for byte (`Q-AN-4`). A re-run reuses the existing file's `test_patterns` list.
5. Adopt refuses, before any write, a stamped `test_dirs` or `test_patterns` that is not a list of strings, naming the
   setting; a stamp is never rewritten or widened.
6. A web file under a `__tests__/` folder, or under a `test/` folder beside a `package.json`, that no written pattern
   matches is counted in one line naming `test_patterns`; no `*.js` pattern is written (`Q-AN-3`).
7. `lint_paths` stays the kit's own scope in both templates and `project_lint_paths` is not written (`Q-AN-1`).
8. `tests/kit/test_adopt_node_tests.py` tests it and joins the `[[testing.map]]` entries of `scripts/agk/tree_walk.py`,
   `scripts/agk/adopt.py` and `scripts/agk/init.py` in this repository's `agk.toml`. Pinned tests change to the new
   answers: three asserts of `tests/kit_dev/test_adopt.py` and `tests/kit/test_survey.py`'s
   `test_rule12_adopt_detect_tests_is_unchanged` (a `.test.js` file is now detected, and a tree with no test and no
   manifest gives the empty list), and `tests/kit_dev/test_init.py`'s import allowlist gains `adopt`, which init
   imports at call time for its detection (kit-only, standard library and kit modules only).

Amendment 231 (`docs/runs/proposed-spec-amendments-231.md`) proposes the words for SPEC-0044 rule 10, SPEC-0002 rule 9
and SPEC-0001 rule 14; it edits no spec.

## Consequences

A Node or TypeScript project's changed test file is selected on its first pull request; a project with no known stack
says so instead of looking for Python names. A Python project's adopt and init output is unchanged. A tree with no test
and no manifest, adopted, now has an empty `test_patterns` and selects no test until a person sets it. A project
already adopted keeps its stamp; `doctor.frontend_lines` names one whose stamp finds no test while web tests are there.

## Residual

- 2026-11-24: a `.js` file under `__tests__/` or `test/` is only counted (`Q-AN-3`); a person decides its pattern.
- 2026-11-24: `.mts` and `.cts` wait for one list shared by `survey.LANGUAGES`, the Node pack and `front_door.py detect`
  (`Q-AN-5`).
- 2026-11-24: the specs change only on the owner's `Maintainer answer: amendment 231 approved`.

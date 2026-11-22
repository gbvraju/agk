# ADR-0698: An added kit script selects the every-script contract tests

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1651, SPEC-0055 rule 6 (widened here), ADR-0692, ADR-0359, red-main brief #1645
- Requirements: REQ-016

## Context

Governance (full) on 330bec63, the merge of #1643, failed with `4 failed, 15183 passed`, all on the new
`scripts/agk/basics.py`, in `tests/kit/test_isolated_mode.py`, `tests/kit/test_installed_imports.py` and
`tests/kit/test_core_contradictions.py`. These tests read every file of `scripts/agk/` by a glob, so no
`[[testing.map]]` entry of a new script lists them and the selection of `scripts/agk/impact.py` did not run them in the
pull request's proof. On main fe55eeee (after ADR-0692) two of them are selected because they name the folder
`scripts/agk/`; `tests/kit/test_core_contradictions.py` still is not
(`python3 scripts/agk/test_plan.py --base 4dceb89e --head 0c5807459fe9`). The tests were written first
(`tests/kit/test_impact_data_files.py`: 12 failed, 34 passed on the unchanged code).

## Decision

1. **The setting.** `[testing] every_script_tests` in `agk.toml` (path class `agk.toml`): a list of test file paths,
   no globs, each a file of the repository; anything else is refused naming `testing.every_script_tests`, never the
   value. Without the key the list is empty, so a project using the kit changes nothing. The kit's own `agk.toml`
   names the three tests above.
2. **The selection** (`scripts/agk/impact.py`, path class `scripts/agk/`). With `profile = "balanced"` and no
   `always_full` match, a file that `git diff --diff-filter=A --no-renames` lists as added under `scripts/agk/` (so a
   renamed file is added at its new path), that is not documentation and not a test file, also selects each listed
   test that exists at the head. The reason printed is `(new script) <path>`. A test already selected keeps its
   reason. A modified script is unchanged (its map entry and ADR-0692 rule select), and a deleted one selects nothing
   new.
3. **What does not change.** `thorough` stays full, `fast` reads only the map, `pr_tests = "all"` and `always_full`
   are as before; a larger selection may reach `full_when_share`, as designed. `execution = "local"` (prepush) and the
   personal-mode sidecar run read the same `impact.py` selection.

## Consequences

A new kit script that breaks isolated mode, the installed imports or the core contradictions fails in its own pull
request's proof instead of on the default branch after merge. A project can name its own every-file tests in the same
setting.

## Residual

- 2026-11-22: SPEC-0055 rule 6 does not name this selection; an amendment that names this ADR is for the spec's
  reviewer group (principle 6).

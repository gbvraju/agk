# Scanner fix: before and after (ADR-0010)

Date: 2026-10-15 (from `date -u`). Item 2 of the day-7 brief. Measured on a fresh `init` target in an empty git
repository, from this tree before the change (origin/main b9d3756) and after it. Throwaway virtual environment outside
the repository: bandit 1.9.4, mypy 2.4.0, flake8 7.4.1, pylint 4.1.3. Commands: `bandit -r . -f json -q`, `mypy .`,
`flake8 .`, `pylint --recursive=y .`, each at the target root with default settings.

## bandit

| | Findings | B101 | B603 | B607 | B404 | Where |
| --- | --- | --- | --- | --- | --- | --- |
| Before | 278 | 247 | 17 | 9 | 5 | B101 in `tests/kit`; the 31 others in `scripts/agk`, `.claude/hooks`, `tests/kit` |
| After | 252 | 252 | 0 | 0 | 0 | all in `tests/kit` |

The brief expected "only the 224 B101" after the fix. The number is higher because the tests grew since the design
note was written (247 asserts before this change, from PRs #14-#18), and this change adds 5 asserts in
`tests/kit/test_scanner_hygiene.py` (252). No finding other than B101 remains. The 31 subprocess findings of the note
are 17 B603 + 9 B607 + 5 B404, as before.

With the printed bandit exclusion applied (`-x ./scripts/agk,./tests/kit,./.claude/hooks`) on a target that also has a
product file, bandit reports nothing and exits 0.

## mypy

Before: 4 errors in 2 files (3 in `check_protected_changes.py`, 1 in `check_adrs.py`). After: `Success: no issues found
in 25 source files`; `scripts/agk` alone: no issues in 13 source files. No `type: ignore` was added.

## The printed snippets, applied

On a copy of the target with a one-line product file `prod.py` and the snippets added to its `pyproject.toml` or command
line: bandit and flake8 report nothing; mypy reports nothing; pylint reports only `prod.py` (docstring and naming).
A first form of the pylint snippet (`ignore-paths` alone) still reported 3 findings in `.claude/hooks/stop_check.py`;
adding `ignore = ['.claude']` fixed it, and the template has both keys.

## Not changed

flake8 (E501 at 79 columns, E203) and pylint style findings on kit code are advisory (Q-ON-4); the kit keeps `ruff`
at 100 columns.

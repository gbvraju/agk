# ADR-0831: A read-only report of the test suite as a whole

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's yes on brief #2007, 2026-11-26T14:54Z)
- Related: ADR-0422, ADR-0441, ADR-0824, ADR-0825, REQ-062, brief #2007, plan #661
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`, `kit/`

## Context

The kit's tests grew from 435 test functions on 2026-10-15 to 11,349 on 2026-11-26, and the governance step that runs them
from about 6 to about 26 minutes (brief #2007's measurement). Every change adds its tests and principle 11 keeps every check,
but no rule, role or command reads the suite as a whole: `test_plan.py` and `test_map.py` choose tests per change, the prepush
record keeps per-file timing (REQ-051 AC1) and `doctor.py` reports a slow single-process suite (REQ-051 AC5). None counts
equal tests, tests that only check a document's wording, or test files that no map entry selects.

## Decision

1. One new installed command, `python3 scripts/agk/test_audit.py [--json] [--since YYYY-MM-DD] [--limit N]`, reads the test
   files of the `[proof]` areas (absent: `tests/` with `test_*.py`) with `ast`, never importing or running them, and prints
   the files, the test functions, the test lines, the code lines of the `[[testing.map]]` `code` entries and their ratio;
   with `--since`, the `def test_` lines local git added and removed since that day (a shallow clone's boundary commits
   left out). It imports only `common` (ADR-0824's set), reads tracked files and local git, makes no network call, writes
   nothing and exits 0; a malformed option exits 2 naming the option, a malformed `[testing]` table exits 2 naming the setting.
2. It prints five lists, each capped at `--limit` names (default 20) with its full count, each a candidate and never a
   verdict: (a) equal tests, bodies without docstrings equal as `ast.dump`; (b) wording-only tests, a test that names a
   `.md` file (directly, through a module constant or through a helper of the same file) whose every assert is an `in` or
   `not in` check, and that calls no kit module, no helper that runs code and no subprocess; (c) brief-pinned names, `brief`,
   `adr` or `amendment` followed by a number; (d) unselected files, named by no `[[testing.map]]` `tests`, `whole_tests` or
   `always_full` glob (`no testing map` without a `[testing]` table); (e) the slowest files of the newest prepush record in
   the clone's `agk-evidence` folder, or `per-file timing: unknown`.
3. The build removes no test. A removal or merge of tests is a later brief per area, reviewed as today, after the owner's
   ruling on Q-TA-1; no test budget is set (Q-TA-2) and the report posts nothing (Q-TA-3).
4. `docs/guides/testing.md` gains "Reading the suite as a whole" and `docs/guides/reference.md` names the command.

## Consequences

The owner and the steward can read the suite's growth and its clean-up candidates at any time, by one command, in the kit
and in a project using it. The lists are pattern readings: a wording-only or equal test may still be wanted, so a person
decides each removal.

## Residual

- Q-TA-1, Q-TA-2 and Q-TA-3 of brief #2007 stay with the owner (2026-11-26).

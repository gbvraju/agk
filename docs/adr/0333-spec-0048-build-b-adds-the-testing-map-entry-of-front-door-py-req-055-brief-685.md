# ADR-0333: SPEC-0048 build (b) adds the testing map entry of front_door.py (REQ-055, brief 685)

- Status: Proposed
- Date: 2026-11-07
- Deciders: maintainers
- Related: ADR-0314, SPEC-0048, SPEC-0038, SPEC-0042, SPEC-0012, ADR-0259, ADR-0271, ADR-0293
- Requirements: REQ-055

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.github/`, `agk.toml`

## Context

Brief #685 is SPEC-0048 build (b), rules 3 and 5: `scripts/agk/front_door.py` (new, installed:
`check-issue`, `discovery-write`, `check-discovery`), the issue form `.github/ISSUE_TEMPLATE/problem.md`
and its line in `kit/manifest.json`, the tests and a changelog fragment. The brief says the build cites
`Covered-by: ADR-0314` (Q-S0048-20) and writes no ADR unless a decision changes, and its `Touches:` line
names `agk.toml` for the `[[testing.map]]` entry every new installed script carries.

ADR-0314 decision 8 lists the classes the builds of SPEC-0048 change and says that no build changes
`agk.toml`. The two cannot both hold for build (b): the kit's own test
`tests/kit_dev/test_intelligent_testing.py::test_every_script_is_covered_by_an_entry_or_always_full`
(REQ-016, brief #578) fails the full suite when a script under `scripts/agk/` matches no `[[testing.map]]`
entry and no `always_full` glob, so a build that leaves `agk.toml` alone cannot pass `prepush.py` (session
rule 31) and is never pushed, and a check is never weakened to go green (principle 11). The conductor's
answer on #685 (2026-11-06T23:24Z, Q-685-2) says that under session rule 36 a build that changes a class
its `Covered-by:` ADR excludes needs an ADR of its own, and that a person rules the point; this is that
ADR, proposed for the person's ruling, and the build is not under `Covered-by: ADR-0314`.

## Decision

1. Build (b) adds one `[[testing.map]]` entry to `agk.toml`, in sorted place: `code =
   "scripts/agk/front_door.py"`, `tests = ["tests/kit/test_front_door_entry.py"]`. No other line of
   `agk.toml` changes: no setting, no table, no value.
2. The entry of decision 1 is this ADR's own exception, scoped to that one entry for `front_door.py`
   in build (b). This ADR says nothing of what ADR-0314 decision 8 means or covers: that reading is the
   maintainers' (Q-685-2, asked on the pull request), and this ADR holds only for the entry it names. Any
   other change of `agk.toml` by a build of SPEC-0048 writes its own ADR, as session rule 36 says.
3. This ADR names every protected path class build (b) changes, the classes of ADR-0314 decision 8 that the
   build touches (`scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.github/`, the issue form and not
   a workflow) and `agk.toml`; the pull request therefore carries no `Covered-by:` line (`check_protected_changes.py`
   passes on an ADR in the same change set that names every class). Every other decision of the build is
   SPEC-0048's as written, recorded under `Decisions taken:` of the pull request.
4. Nothing of ADR-0314 is superseded: its decisions 1 to 7 stand, and decision 8 stands for every other
   build.

## Consequences

`front_door.py` is mapped, so `test_plan.py` selects its tests when it changes and the REQ-016 test passes.
The maintainers rule Q-685-2 on the pull request, and after their ruling the next verdict carries or
withholds the `Final:` line for this ADR; a withheld line removes the entry, and the script stays unmapped
until ADR-0314 is amended.

## Residual

Whether ADR-0314 decision 8 covers the testing map is Q-685-2, a maintainers' question this ADR does not
answer. If they rule that it does, the fix is one amendment of ADR-0314 and the removal of this entry,
and `always_full` would then be the only other place to cover the script (due 2026-12-31).

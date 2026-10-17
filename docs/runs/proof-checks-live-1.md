# Proof checks: live run 1, criterion b (SPEC-0010 rules 1 to 6 and 21)

Date: 2026-10-16 (from `date -u`). The check of part (a), run read-only on this repository at the commit `8bdbbe3da9d0f79c909ef8c1096e4983b039358a`
(the code commit of the pull request that adds it; `docs/requirements.md` is the one on `main` plus the AC4 of REQ-003, and `ac_coverage = "block"` in `agk.toml`).

## 1. This repository, in block mode

```
$ python3 scripts/agk/check_requirements.py
ok requirements (20 requirements)
$ echo $?
0
```

Both `done` requirements comply: REQ-001 (AC1 to AC3) and REQ-003 (AC1 to AC4: AC4 was added on the ruling of Q-K4-121 and the fixture test of the check carries its marker) have a marker for every criterion. **No `done` requirement
fails, so no status is changed in the pull request** and `block` is set in this repository's `agk.toml` (Q-K4-20).

The drift audit at the same commit:

```
$ python3 scripts/agk/drift_audit.py --today 2026-10-16 | head -1
agk drift audit 2026-10-16 (window 2026-10-09 to 2026-10-16): findings=0 D1=0 D2=0 D3=0 D4=0 D5=0 D6=0 D7=0
```

No stray marker (`D7`) exists. Two existing tests wrote data that looked like markers (`REQ-001 AC9`, and `REQ-9nn ACn` in the refactor tests); the
data is now written so that no line of those files is a marker (Q-K4-125).

## 2. The list of rule 6, recomputed (every requirement as if it were `done`)

This is what `block` would fail if the maintainers set the requirement `done` today. Only REQ-001 and REQ-003 are `done`.

| Requirement | Status | Criteria with no `REQ-nnn ACn` marker |
| --- | --- | --- |
| REQ-001, REQ-003 | done | none (REQ-003 AC4 is covered by `tests/kit/test_check_requirements_ac.py`) |
| REQ-002, REQ-004, REQ-006, REQ-007, REQ-009, REQ-010, REQ-011, REQ-012, REQ-014 | not done | none |
| REQ-005 | planned | AC3 |
| REQ-008 | planned | AC1 |
| REQ-013 | planned | AC4 |
| REQ-015 | planned | AC2 (the sandbox run of rule 21 (c), a record) |
| REQ-016 | planned | AC2, AC3 |
| REQ-017 | planned | AC1 |
| REQ-018 | planned | AC1 |
| REQ-019 | planned | AC1, AC2 |
| REQ-020 | planned | AC1, AC2, AC3 |

Against rule 6 of 2026-10-16: REQ-005 AC3, REQ-008 AC1 and REQ-013 AC4 are still short, as then; REQ-015 AC1 and AC3 and REQ-018 AC2 now have a
marker (the tests of this and the earlier pull requests).

## 3. The fixture: a `done` requirement whose second criterion has no test

A `done` requirement `REQ-007` with `AC1` and `AC2` and the marker `REQ-007 AC1` only, in a throwaway repository:

```
$ python3 scripts/agk/check_requirements.py        # ac_coverage = "block"
FAIL requirements: REQ-007: done requires a test marker for AC2
$ echo $?
1
$ python3 scripts/agk/check_requirements.py        # ac_coverage = "warn"
warn requirements: REQ-007: done requires a test marker for AC2
ok requirements (1 requirements)
$ echo $?
0
```

The message names the requirement and the criterion id and not the criterion's text. The same fixture is `tests/kit/test_check_requirements_ac.py`.

## 4. The sandbox (SPEC-0010 rule 21 (c))

Date: 2026-10-16 (from `date -u`). The sandbox (`gbvraju/agk-sandbox`, installed on kit 0.9.0, HEAD `15330b1`) was attached to the session
with `add_repo` (read access) after #58 and #59 merged. The kit's `check_requirements.py` of `main` (a11eaf3) was run from the
sandbox work tree, read-only (`PYTHONDONTWRITEBYTECODE=1`; `git status --short` is empty before and after):

```
$ python3 <agk>/scripts/agk/check_requirements.py        # the sandbox's agk.toml has no ac_coverage: warn
ok requirements (5 requirements)
$ echo $?
0
```

Then in a throwaway local clone of the sandbox with `ac_coverage = "block"` appended to its `agk.toml`:

```
$ python3 <agk>/scripts/agk/check_requirements.py
ok requirements (5 requirements)
$ echo $?
0
```

The sandbox has no `done` requirement (REQ-001 to REQ-003 inherited from the template and its own REQ-101 and REQ-102 are all
`planned`), so nothing can fail. Read as if each were `done`, every criterion has a marker (REQ-101 and REQ-102 by
`tests/test_wordcount.py`); no requirement would fail in `block` mode, and **no status needed setting back**.

One finding for the sandbox's own drift audit: 239 stray markers (`D7`), all in the 17 kit test files under `tests/kit/` that the kit
installed there (`tests/kit/test_drift_audit.py` 37, `test_review_context.py` 32, `test_metrics.py` 29, ...): their fixtures
write `REQ-nnn ACn` for requirements the sandbox does not have. Strays never block (rule 4); they would show as `D7` findings in the
sandbox's weekly audit. In `adopt` mode `tests/kit` is excluded from the search; in `init` mode it is not. Recorded as a question
for the maintainers (Q-K4-134 in ADR-0026); nothing was changed in the sandbox.

## 5. The proof check on this repository, after Q-K4-133 was ruled

Date: 2026-10-17 (from `date -u`). `project_tests` of this repository now runs the kit tests (`AGK_KIT_TESTS=1 python3 -m pytest -c
tests/kit/pytest.ini tests/kit tests/kit_dev -q`). `proof.py --base origin/main` was run on the branch of the pull request that adds it
(base `a11eaf3`; the tests of the pull request placed on the base; each run took 9 to 10 minutes of the 900 seconds allowed).

First run, on the commit that changed `agk.toml`:

```
$ python3 scripts/agk/proof.py --base origin/main
proof: not-proven (red-on-head)
exit=1        # run 1 (base): 39 failed, 821 passed, 3 skipped; run 2 (head): 2 failed, 860 passed, 3 skipped
```

The head was red: two kit-only tests (`test_ac2_make_test_and_testpaths_cover_all_of_tests`, `test_ac1_templates_carry_project_tests_and_no_pyproject_stamp`)
still asserted the old `project_tests` of this repository's `agk.toml`. The check found a defect of the change that the pull request's own
tests had not exercised (`make test` was not yet run on that commit). They were corrected.

Second run, on the corrected commit:

```
$ python3 scripts/agk/proof.py --base origin/main
proof: proven
exit=0        # run 1 (base): 40 failed, 820 passed, 3 skipped; run 2 (head): 862 passed, 3 skipped
```

So for a real change with its tests here the check now reads `proven`; before Q-K4-133 it read `not-proven (green-on-base)` on every pull
request (the same command run on the earlier head of the pull request, recorded in ADR-0026). The `proof` job of the pull request itself
reads the same way on CI.

## 6. Not done here

- The first real `proof` job and the seeded pull requests of SPEC-0010 rule 20 are recorded in `docs/runs/proof-checks-live-2.md`, a docs
  pull request of its own, after the pull request of part (b) is merged.


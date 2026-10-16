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

## 4. Not done here

- The sandbox run (rule 21 (c)) needs the sandbox attached to a session; it is asked for in the pull request report and is not assumed.
- The sandbox record is added to this file through the pull request of part (b), after this one is merged.

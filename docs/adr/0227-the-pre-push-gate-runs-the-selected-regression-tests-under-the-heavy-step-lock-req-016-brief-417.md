# ADR-0227: the pre-push gate runs the selected regression tests too, under the heavy-step lock (REQ-016, brief 417)

- Status: Proposed
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0186, ADR-0191, ADR-0208, ADR-0220
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #417 (from #289 parts 2 and 4, and #288 tier T0): `prepush.py` (ADR-0186) runs only proof's plan, the pull request's
own test files. `impact.py` (ADR-0220, brief #373) now gives the regression set that the `[testing]` table of `agk.toml`
selects, but nothing runs it. In the pilot two builders' gates collided on one laptop; `lock.py` (ADR-0191) exists, but
prepush does not use it. The script and its tests are protected path classes, so this ADR names them. The tests were
written first (`tests/kit/test_prepush_regression.py`: 14 failed, 2 passed at the first checkpoint).

## Decision

1. **The regression set runs after proof's runs (answer 1).** With a `[testing]` table, the `tests` step of `prepush.py`
   first makes proof's runs (the plan `test_plan.py` prints), then the regression set of `impact.py` for the merge base and
   `HEAD`. When the set is full, `project_tests` runs once in the top folder. Otherwise each `[proof]` area, in table order,
   runs the selected files that its `dirs` and `patterns` match, through its `command` with `{files}` filled in by proof's
   own `area_command`, in its `cwd`. A selected file that no area matches is printed as
   `tests: not run (in no [proof] area): <file>` and marks the step `not run`, so the run ends
   `prepush: passed; not run: tests` (Q-417-4). Without a `[proof]` table a non-empty selection runs `project_tests` once,
   since no area can take single files (Q-417-3). An unmapped file is printed as in the plan, and an empty set is said
   (`tests: regression: nothing selected`, with `(only documentation changed)` for a docs-only change). When `project_tests`
   is needed but not set, it is printed as not run and marks the step `not run`.
2. **One line per run (answer 2).** Each run prints, when it ends, `prepush: tests <area or full> ok|FAIL (<s>s): <reason>`.
   The reason of a regression run is the rule that selected it: the full reason of `impact.py` (`always_full <glob> matches
   <file>`, `profile thorough`, `profile balanced: <n> unmapped file(s)`), or, per area, each distinct
   `<changed> matches code <glob>, tests <globs>` joined by `; `. A proof run gives `the pull request's own test files (the
   proof plan)`. The step stops at the first failing run with its output, or with proof's timeout note; each run keeps
   `proof_timeout`. The `--record` file lists every run, as before, with two added keys, `set` (`proof` or `regression`)
   and `reason`.
3. **The heavy-step lock (answer 3).** With the table, the whole `tests` step holds the lock `heavy` of `lock.py`, in its
   folder (`lock_dir`) and with its stale rule (`lock_stale_minutes`), taken by lock.py's own `take`, which prints its
   one-line `lock heavy: waiting; ...` and `lock heavy: taken` messages; the owner's session is `AGK_SESSION`, as in
   `lock.py`. The lock is released when the step ends, also on a failing test, an interrupt or a termination signal. A gate
   whose caller already holds the lock (`lock.py run --name heavy -- prepush.py`, session rule 31: the lock's `child` is
   this process, or its `pid` is this process's parent, on this host) prints
   `lock heavy: held by this run's caller (lock.py run); not taken again` and does not wait for itself (Q-417-2).
   `--no-lock` leaves the lock out, for CI. A refused `lock_dir` or `lock_stale_minutes` fails the step naming the setting.
4. **Unchanged paths (answer 4).** `--quick` skips every test and takes no lock. Without a `[testing]` table the step runs
   exactly as before: proof's plan alone, the same lines, no regression set and no lock (Q-417-1).
5. **The guide (answer 5).** `docs/guides/testing.md` gains a section `The pre-push gate`, and its opening no longer says that
   nothing runs the selection.

## Consequences

- A project with a `[testing]` table runs, before a push, the tests that guard the changed code, and sees why each set ran.
- Two gates on one machine no longer run their tests at once; the second waits and says for whom.
- A project without the table sees no change.
- `impact.py` and `test_plan.py` still say in their docstrings that nothing runs the selection; they are outside the brief's
  `Touches` and left as they are (Q-417-5).

## Residual

- Q-417-1 (2026-10-31): answer 3 says the step holds the lock and answer 4 says that without a `[testing]` table it runs
  exactly as today; read conservatively, without the table the step takes no lock either. Session rule 31 still wraps the
  gate in `lock.py run --name heavy` on a shared machine.
- Q-417-2 (2026-10-31): session rule 31 runs the gate as `lock.py run --name heavy -- prepush.py`; taking the lock again
  inside would wait for its own caller until the lock is stale (120 min) and then clear it. The gate recognises its caller's
  lock and does not take it again. Not in the brief; the narrowest reading that keeps rule 31 and answer 3 both working.
- Q-417-3 (2026-10-31): a selection of single files without a `[proof]` table has no area command to run them; read as
  "when unsure, run more" (ADR-0220), `project_tests` runs once and the reason says why.
- Q-417-4 (2026-10-31): a selected file in no area is listed and, read conservatively, also marks the step `not run`, so the
  gate ends `passed; not run: tests` rather than `all steps passed`.
- Q-417-5 (2026-10-31): `docs/guides/reference.md` lists the options of `prepush.py` without `--no-lock`, and the
  docstrings of `impact.py` and `test_plan.py` say nothing runs the selection yet; all three are outside `Touches` and
  unchanged here.

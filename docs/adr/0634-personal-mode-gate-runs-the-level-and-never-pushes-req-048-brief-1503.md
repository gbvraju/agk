# ADR-0634: Personal mode's gate runs the steps of the level, records them and never pushes

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: ADR-0267, ADR-0208, ADR-0632, SPEC-0041, SPEC-0010, brief #1503
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0041 rule 17 names five levels and rule 18 a floor that runs at every level; rule 19 asks that `/agk:personal
push` runs the gate of the level on the head, writes `records/gates/<head>.json` in the schema of `prepush.py
--record` and on a pass prints the `git push` command for the developer, never pushing (rule 20); rule 23 asks for one
event per step. On main `personal.py floor` ran the two floor steps and only printed the level, and nothing wrote a
gate record, so `report` could not flag a branch pushed without one. ADR-0267 asks each build of the spec for its own
ADR naming its classes; this is build (h), part 2.

## Decision

1. `personal.py gate [--clone DIR] [--sidecar DIR] [--base REF] [--approve]` runs nothing without `--approve` (the
   person's yes, as `baseline` and `floor` take it) and then prints what it would run. With it, on the head tree that
   `git archive` writes into the sidecar's `cache/trees/` (rule 4), it runs the floor of rule 18 unchanged at every
   level, then by `[personal] level`: `tests-first` adds the proof step, the branch's added or changed test files
   (`survey.detect_test_files`) placed on the base tree by `proof.place_tests` and judged by `proof.decide`, red on
   the base then green on the head; `spec` adds a spec of the sidecar that is `Approved` and confirmed at a terminal
   (`reviewers.derived_only`, ADR-0632) before the committer time of the branch's first commit; `review` adds the
   review context and the reviewer report under `records/reviews/` of the sidecar, checked by `check_review_report`
   unchanged, and a terminal comment by the one person whose first two lines are `Confirmed: <head>` and `Verdict:
   cleared <head>`; `evidence` re-reads the written record with `evidence.parse` and `evidence.problems` unchanged.
   A missing or failing step fails the gate naming the step and the setting `personal.level`, never a value.
2. The gate writes `records/gates/<head>.json` (schema 1 of `prepush.py --record`: head, base, started, tree_clean,
   versions, steps, notes, result, and the level), appends one event per step and one for the gate to
   `metrics/events.jsonl`, and makes one sidecar commit of those two paths. A failed gate still writes its record.
3. It never pushes: on a pass it prints `git push <remote> <branch>` for the developer to run; no argument list of
   `personal.py` holds `push`. With `[personal] team_refs` off (the default) it prints a warning naming the setting for
   each commit of the branch that carries an `Advances:` line or a path of the sidecar layout (rule 20).
4. `personal.py report` adds `report: pushed without a gate: <branch>` for each local branch whose head equals its
   upstream's remote-tracking ref, read without a fetch, and that has no gate record (rule 19).
5. Nothing is written in the product clone or under its `.git/`: every git call is read-only with
   `--no-optional-locks`, and no worktree is added. So `proof.py`'s two worktrees and `evidence.py check`'s worktree
   re-run are not run; their judging functions are reused unchanged.
6. `agk.toml` maps `scripts/agk/personal.py` to `tests/kit/test_personal_gate.py`.

## Consequences

Each level above `light` now adds its steps, a gate record exists per gated head, and `report` names a branch pushed
without one. The `review` level stays advisory in what the reviewer finds (`Q-S0041-10`): the gate needs the report to
be well formed and the person's verdict on the head, not a reviewer's `cleared`.

## Residual

- 2026-11-18: the plugin command `/agk:personal push` is the user-scope packaging of build (l); here the gate is
  `personal.py gate`, which that command runs.
- 2026-11-18: `personal.py change start|review` (build (i)) is what will write the review files and the person's verdict
  that the `review` level reads; until then a person writes them.

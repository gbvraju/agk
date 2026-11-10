# ADR-0426: Personal mode records each floor run and reports the defects caught before a push

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0267, ADR-0406, SPEC-0041, brief #999
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

SPEC-0041 rule 23 asks each gate to append one event to `metrics/events.jsonl` in the sidecar and `personal.py report`
to count, on demand, the defects caught before a push, with `unknown` where there are too few events. The floor of rule
18 (ADR-0406) printed its result and wrote nothing, and there was no `report` command. ADR-0267 asks each build of the
spec for its own ADR naming its classes; this is build (k), first part.

## Decision

1. `personal.py floor ... --approve`, after its result line, appends one JSON line `{"head", "step": "floor", "result":
   "passed" | "failed", "time"}` (UTC, Z form) to the sidecar's `metrics/events.jsonl`, created `0600` under `0700` as
   `survey.write_private` does. A floor without `--approve` appends nothing. An append that fails prints one line
   naming the file and keeps the floor's exit code. Nothing is written in the clone or under its `.git/`.
2. `personal.py report [--week YYYY-Www] [--clone DIR] [--sidecar DIR]` reads the events of the ISO week given (the
   current UTC week when left out). A defect is a failed floor head of that week followed, at the same time or later,
   by a passed floor head that descends from it (`git merge-base --is-ancestor`, the heads differ, no fetch); each
   failed head counts once. Under two floor events in the week the count is `unknown`, never `0`.
3. A line that is not a JSON object with exactly the four fields (a 40-hex head, a passed or failed result, a Z-form
   time) is skipped and counted in one line. A `--week` not of the form, or not a real ISO week, is refused naming the
   option. Review findings, rework and time per change print `unknown`, naming build (k)'s second part; the baseline
   prints `unknown (the attach time is not recorded)`, as the registry records no attach time. The last line is the
   correlation sentence. `report` writes nothing and runs no test.

## Consequences

A developer can see each week how many floor failures were fixed before they pushed. The count is a lower bound: a
failure fixed by a rebase that drops the failed head is not counted.

## Residual

- 2026-11-10: the registry (`personal_state.py`) records no attach time, so the baseline is always `unknown` until a
  later build records one; `personal_state.py` is not changed here (answer 5).
- 2026-11-10: a failed head never followed by a pass is not a defect caught, and is not reported separately.

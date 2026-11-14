# ADR-0519: The estimator fits a deadline by builder count before history exists

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0043 rules 13, 14 and 26, ADR-0269, ADR-0465, brief #1220, plan #661, amendment 177
- Requirements: REQ-050

## Context

`scripts/agk/plan_estimate.py` prints `uncalibrated` with the declared `Expected:` sums and the finish `unknown` while
the project has no merged history (SPEC-0043 rule 14), and it has no builder count. In a customer trial the go-live fit
for 4, 6 and 8 builders against a deadline was therefore worked out by a model in chat, with its assumptions in a file
outside the repository. The owner asked that both planning scenarios (a vision brainstormed into a plan, and a working
prototype turned into briefs) end with the plan's own fit of capacity to a deadline.

## Decision

1. `plan_estimate.py --deadline D --builders N[,N...] [--hours-per-day H] [--review-hours R]` (H 6, R 0.25 by
   default) is the uncalibrated path only: with a calibrated history (rule 12's minimums met for the sizes of the brief
   files) it exits 2 naming `--deadline`. It is never combined with `--with`; each bad option exits 2 naming the option,
   never its value.
2. It reads every brief file `docs/plan/briefs/M<n>/<key>.md` of the milestones of `milestones.md` in order, each
   costing the mid point of its `Expected:` range (the `[plan] default_hours` range of its size, else 0 h, both counted)
   plus R hours of review, with its `Depends-on` keys (a value that names no brief file, such as `#12`, is taken as done
   and counted) and its `Touches` and `Adds` entries less the shared-mechanical paths (`session.shared_patterns`).
3. A list schedule in milestone then key order starts a brief only when its dependencies are done and no running brief's
   entries overlap its own by the prefix rule of `session.overlap`. With N builders the finish is the soonest of the
   schedules of 1 to N lanes, so more builders never finish later; a `Depends-on` cycle exits 2 naming `--plan`.
4. Hours become working days at H a day, Monday to Friday with no holidays, from the first working day after `--today`
   (rule 13's convention). Per N, ascending, it prints `builders N: finish <date>, buffer <n> working days;` then
   `meets the deadline` or `to meet the deadline move <M/key, ...>`: the latest brief first, each with the briefs that
   depend on it, until the rest meets D, listed in plan order.
5. The output starts `internal estimate: deadline D for builders ... from <today>`, names every assumption on one
   `assumptions:` line, ends with rule 26's limits line and is printed only: nothing is written, into `docs/` or
   elsewhere. The same inputs print the same bytes.

## Consequences

The owner chooses capacity from the plan's own files before any history exists, with every assumption printed beside the
answer. The calibrated estimate, `--with` and every other output are unchanged. `tests/kit/test_plan_estimate_fit.py`
checks one lane at the summed hours, the review and day hours, side-by-side briefs, dependencies and overlapping
`Touches` serialising (shared paths not), more builders never later, a deadline miss and its moves with their
dependents, the output's first, assumptions and last lines, the owner default, determinism with nothing written, and
the refusals. Protected path classes changed: `scripts/agk/` (`plan_estimate.py`) and `tests/kit/` (the tests). No
workflow changes.

## Residual

- 2026-11-14: SPEC-0043 gains the fit only through amendment 177 (`docs/runs/proposed-spec-amendments-177.md`), for the
  maintainers' decision (due 2026-12-31).
- 2026-11-14: holidays, part-time builders and a brief file of a brief already closed are not modelled; a closed brief's
  file counts until the person removes it (due 2026-12-31).

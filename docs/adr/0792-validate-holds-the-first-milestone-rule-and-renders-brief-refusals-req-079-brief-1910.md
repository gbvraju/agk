# ADR-0792: Validate holds the first-milestone rule and render's brief refusals (REQ-079)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers
- Related: SPEC-0072, SPEC-0043, brief #1910, brief #1587, brief #1594, plan #661, ADR-0667, ADR-0674, ADR-0456, ADR-0461, ADR-0472
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (`check_plan.py`, `plan_intake.py`), `tests/kit/`
(`test_skeleton_basics.py`, `test_foundation_kind.py`, `test_plan_slices.py`, `test_plan_intake_clean.py`) and
`agk.toml` (two `[[testing.map]]` test entries of `scripts/agk/plan_intake.py`). `kit/hashes.json` is not edited by hand.

## Context

SPEC-0072 rule 4 holds two plan rules: one foundation brief in the first milestone that the milestone's other briefs
depend on (brief #1587, ADR-0667), and a slice brief after it in that milestone (brief #1594, ADR-0674). The first had
two copies, one in `plan_intake.py validate` and one in `check_plan.py`; the second was only in `check_plan.py`. A
work-type plan whose first milestone held only the foundation passed `validate` and `render` and was refused by
`check_plan.py` after it was written (the prototype-to-build run PB-07). In the same way each brief refusal of
`render` (rule 7) passed `validate` (the idea-to-build run IB-13).

## Decision

1. `check_plan.first_milestone_problems(declared, first, briefs)` holds both rules once, over a list of
   `(key, milestone, kinds, depends_on)`, and returns `(code, key)` pairs. `check_plan.foundation_problems` and
   `slice_brief_problems` read the brief files for it; `plan_intake.foundation_problems` reads the proposals
   (`foundation` and `slice` true, `first` = `M1`). Each reader keeps its words; `validate` and `render` gain
   `rule 5: briefs: the first milestone has no slice brief after the foundation (setting: work_type)`.
2. `render_problems` splits: `brief_form_problems` (the key a file name, `touches` and `advances` not empty, the title
   at most 300 characters, an area name with a letter or digit) runs in `validate` with render's `rule 7:` text, and
   `render_problems` keeps only `milestone is not set`, the draft state `validate` accepts (ADR-0472).
3. A later brief rule of `check_plan.py` that a proposals file can break joins `first_milestone_problems` or a function
   both readers call; a parity test renders six plans and compares the two readers' verdicts.

## Consequences

A plan that `validate` accepts renders and passes `check_plan.py`'s first-milestone rules. With a work type and no
briefs at all, `validate` no longer says `no foundation brief`; `check_plan.py` never did, and a milestone with no brief
is refused by rule 5 already. No spec text changes.

## Residual

- `Q-PS-3` (2026-11-24): may one brief be both foundation and slice, and may M1 hold two slice briefs? Unchanged in both
  readers; the maintainers may rule a stricter count.
- `Q-PS-5` (2026-11-24): with a refused `work_type`, `validate` passes a plan with no foundation while `check_plan.py`
  prints `not run plan work-type rules`. Unchanged here.

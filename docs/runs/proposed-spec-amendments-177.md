# Proposed spec amendments 177 (SPEC-0043; REQ-050)

Date: 2026-11-14 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0519 (brief #1220), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md`. Brief #1220
reserved ADR-0519 and amendment 177. This pull request does not edit the spec; the maintainers apply the line if they
approve it.

The sentence (brief #1220): "Before any history exists, the estimator shows, for a deadline, the finish date at each
number of builders, so the owner chooses capacity from the plan instead of from a hand calculation."

## What is on the default branch today

Read in the code by this session on `origin/main` (76fcd1b): `scripts/agk/plan_estimate.py` prints, for an uncalibrated
milestone, `uncalibrated`, its reasons, `declared <low>-<high> hours` and `finish unknown` (rule 14), and has no option
for a deadline or a number of builders.

## Items

1. **Rule 14, one amendment line.** "Before a calibrated history, `plan_estimate.py --deadline D --builders N[,N...]
   [--hours-per-day H] [--review-hours R]` (6 and 0.25 by default) prints an internal estimate, refused with exit 2
   naming `--deadline` once the history is calibrated: from the brief files' `Expected:` mid points (the owner default,
   else 0 h) plus R, their `Depends-on` and their `Touches` and `Adds` less the shared-mechanical paths, a list schedule in
   milestone then key order that never starts a brief before its dependencies or beside an overlapping one, the soonest
   of 1 to N lanes, in working days Monday to Friday at H a day from the first working day after `--today`; per N its
   finish date, its buffer in working days against D and, on a miss, the latest briefs (with their dependents) to move
   for the rest to meet D. The output starts `internal estimate`, names every assumption on one `assumptions:` line, ends
   with rule 26's line and is never written into `docs/`."
2. **No other change.** Rules 12, 13, 15, 16, 21 and 26, the calibrated output and `--with` stay as they are.
3. **Tests.** `tests/kit/test_plan_estimate_fit.py` (ADR-0519's Consequences).

# Proposed spec amendments 156 (SPEC-0047; REQ-058)

Status: proposed

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
SPEC-0051 build (d), brief #903, `Covered-by: ADR-0340`, as SPEC-0051 rule 9 says. The path:
`docs/specs/0047-every-repository-has-one-weekly-scorecard-of-numbers-with-thresholds-and-trends.md`. The number 156 is the one
brief #903 reserved. Nothing here is applied to a spec in this pull request; the owner decides it, and it needs a person's
`Approve:`; no session posts it.

## SPEC-0047

1. **Rule 1, a metric added after `stale_guides`.** Add: "`goals_not_met`: the number of `not met` goals in `accepted` records
   on the default branch on the run date, read from the files with the reader of `check_acceptance.py` (SPEC-0051 rule 9); a
   stale or proposed record counts in no number. Its line is `0` by default, `(verify)` as rule 3 marks every default, so any
   unmet goal is a level finding and opens the one `scorecard: goals_not_met` issue of rule 5. The scorecard section adds one
   information line, `acceptance: <met> of <total> goals met in <k> records`, or `acceptance: no record` with value `0`."

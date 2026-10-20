# Proposed spec amendments 28 (SPEC-0007 rule 8, SPEC-0009 rule 14, SPEC-0015 rule 4)

Date: 2026-10-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0059. SPEC-0018 rule 9 names the first; the other two follow from it. The paths: `docs/specs/0007-metrics.md`, `docs/specs/0009-facts.md` and `docs/specs/0015-when-more-than-ten-pull-requests-merged-in-the-week-the-repo.md`.

1. **SPEC-0007 rule 8, the supporting fields.** Three fields are added to the metrics table, after `hours_open_to_merge`: `actual_hours`, `estimated_size` and `estimated_hours` (the text is in rule 8 of
   `docs/specs/0007-metrics.md`). Rule 14 needs no change: it says the table has the fields of rules 2 to 9 as columns. `hours_open_to_merge` and `cost_class` are unchanged.
2. **SPEC-0009 rule 14, the pull request row.** The row gains `estimated_size`, `estimated_hours` and `actual_hours` (SPEC-0018 rule 5), and the sentence that the body is read for the `Behaviour:` line and
   for nothing else becomes: read for the `Behaviour:`, `Size:` and `Expected:` lines and for nothing else (Q-K4-214). `kit/facts-schema.json` gets the three optional properties (SPEC-0009 rule 19);
   `schema` stays 1 (SPEC-0018 rule 5).
3. **SPEC-0015 rule 4, the busy-week totals line.** "With its text exactly as today" becomes "with its text exactly as today (with the ending of SPEC-0018 rule 6)": the totals line of a busy week ends
   with the same estimate ending as a quiet week's. Nothing else of the rule changes.

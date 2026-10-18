# Proposed spec amendments 23 (SPEC-0004, SPEC-0009, SPEC-0010 and SPEC-0011; Day 14 E2)

Date: 2026-10-18 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). The paths:
`docs/specs/0004-drift-audit.md`, `docs/specs/0009-facts.md`, `docs/specs/0010-proof-checks.md`, `docs/specs/0011-inbox-and-report.md`.

**Applied by ADR-0036** (2026-10-18). It closes the two residuals of the product report: the Proven line prints the proof reason (due
2026-11-15), and the facts carry a path for each spec and ADR so that inbox lines link the file (due 2026-11-30; proposals 18, item 2).

1. **SPEC-0010 rule 17.** The names of the `not-proven` and `unknown` outcome steps carry the reason of `proof.py` in parentheses:
   `outcome: not-proven (red-on-head)`. The run step writes a second output, `reason` (empty for `proven` and `skipped`).
2. **SPEC-0009 rule 14.** Each pull request object gains `proof_reason`: the reason word, `null` for `proven` and `skipped`, `"unknown"`
   when the outcome could not be read or the step name carries no reason (a run made before the names did).
3. **SPEC-0009 rules 10 and 11.** Each spec and ADR object gains `path`.
4. **`schema` stays `1`** (SPEC-0009 rule 19). Both additions are optional properties in `kit/facts-schema.json`; no released consumer reads
   either (the renderer of kit 0.15.0 to 0.17.1 ignores keys it does not know), and the renderer of this change treats a document without
   them as it did before (the directory link; `reason unknown`). A change to the meaning or removal of a key would raise it.
5. **SPEC-0011 rule 9.** The Proven line prints the reason after `not-proven` and after `unknown`, with a plain-language gloss for the five
   reasons; a reason without a gloss is printed as it is; a missing or unknown reason reads `reason unknown`.
6. **SPEC-0011 rules 3 and 11.** Inbox lines for a Draft spec and a Proposed ADR link the file (`path`) at the facts commit; with no `path`
   in the document they link the directory, as before.
7. **SPEC-0004 rule 9, retiring a delivered bullet** (the maintainers' ruling of Q-K4-172). D4 skips a dated `## Residual` bullet of an ADR or a
   spec when a row of the register's `## Closed` table names that source and that text: the first cell is the bullet's file, the second is
   the bullet's text without its leading `YYYY-MM-DD: ` and its trailing `(due YYYY-MM-DD)` (or the whole bullet text), whitespace collapsed,
   otherwise an exact match; another text, another source or another case does not close it. `facts.py` marks the same bullet
   `"state": "closed"` in `residuals`, so the report's Needs-you and At-risk sections drop it (SPEC-0009 rule 12).

# Proposed spec amendments 17 (SPEC-0009; found while building the proof checks, SPEC-0010 (a))

Date: 2026-10-16 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). The path:
`docs/specs/0009-facts.md`.

**Applied by ADR-0024** (2026-10-16) on the maintainers' ruling of `Q-K4-122`.

## SPEC-0009 (`docs/specs/0009-facts.md`)

1. **Rule 15, the kinds counted by `drift`.** The audit gained a finding kind `D7` (SPEC-0010 rule 4: stray markers, and in `warn` mode
   shortfalls of acceptance coverage). Rule 15 names `D1` to `D6`. Proposed: the counts hold every finding kind the audit defines
   (`drift_audit.CODES`; `D1` to `D7` today), each present and `0` when it has no finding, and `total` is the number of findings of all
   those kinds. A kind added to the audit later is counted by the same sentence and changes `kit/facts-schema.json`.
2. **Rule 20, the `drift-counts` case.** "with known counts for D1 to D6" becomes "with known counts for every kind the audit defines".
3. **`schema` stays `1`.** SPEC-0009 rule 19 says a change to a key raises `schema`. No consumer reads the document yet (SPEC-0010 to
   SPEC-0013 are not built), so the change is made inside schema 1 by the maintainers' ruling; from the first consumer on, a change
   raises it.

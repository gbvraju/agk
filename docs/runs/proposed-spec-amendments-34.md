# Proposed spec amendments 34 (SPEC-0011 rules 8 and 13; REQ-029 part R1)

Date: 2026-10-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0070. The path: `docs/specs/0011-inbox-and-report.md`.

1. **SPEC-0011 rule 8, the sections.** The report is built as a structure of items and rendered from it (SPEC-0022 rules 2 to 5). In this part the opening, Delivered, Proven, Cost and the footer (the
   notices) are items of the fixed kinds; Needs you and At risk are still lines of text (the transitional kind `line`, removed in part R2). The printed text does not change.
2. **SPEC-0011 rule 13, the tests of the renderer.** A test renders the markdown from the structure alone, also after a trip through JSON, and compares it with what the script prints. The imports and the single
   file read of (b) are unchanged.

# Proposed spec amendments 25 (SPEC-0014 rule 5)

Date: 2026-10-20 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0050. The path:
`docs/specs/0014-the-weekly-product-report-names-the-kit-version-it-was-rende.md`.

1. **SPEC-0014 rule 5, "The inbox output has no footer and does not change."** The inbox output does have a footer of its own: the line `facts: <commit>` and, when the tree is dirty,
   the notice (`footer_head` in `product_report.py`, shared with the report; the inbox goldens end with it). Only the first half of the sentence is wrong; the second half, that the
   inbox output does not change, is what the tests and the goldens hold. Conservative reading (Q-K4-202): the `kit version:` line is part of the report's footer only, and the inbox output
   is byte-identical to before. New wording of the first sentence: "The inbox output has no `kit version:` line and does not change." The meaning of rules 4 and 5 is unchanged.

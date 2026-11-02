# Proposed spec amendments 110 (SPEC-0011, SPEC-0014, SPEC-0015, SPEC-0016, SPEC-0017, SPEC-0019, SPEC-0022, SPEC-0024, SPEC-0026; REQ-039)

Date: 2026-11-01 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0244 (brief #385), which stays `Proposed` for the maintainers' decision. The person accepted the fold on #278 (row 9 of the
decision table, 2026-11-01). The paths: `docs/specs/0011-inbox-and-report.md`,
`docs/specs/0014-the-weekly-product-report-names-the-kit-version-it-was-rende.md`,
`docs/specs/0015-when-more-than-ten-pull-requests-merged-in-the-week-the-repo.md`,
`docs/specs/0016-at-risk-shows-one-line-per-kind-of-pull-request-risk.md`,
`docs/specs/0017-delivered-lists-only-the-requirements-that-became-done-in-the-week.md`,
`docs/specs/0019-the-weekly-product-report-also-publishes-the-facts-document.md`,
`docs/specs/0022-the-weekly-product-report-also-publishes-the-sections-it-com.md`,
`docs/specs/0024-the-report-s-cost-totals-carry-the-number-of-the-week-s-merg.md`,
`docs/specs/0026-each-section-of-the-weekly-report-each-grouped-item-in-it-an.md`.
It needs a person's `Approve: SPEC-0011` (SPEC-0032: a person approves every spec); no session posts it. No rule's meaning
changes and nothing about the report's output changes.

1. **SPEC-0011 gains eight sections.** After rule 23, one section per spec, in the order the specs were approved, headed
   `### From SPEC-NNNN: <its title>`, holds that spec's rules as numbered rules of SPEC-0011, each with its text after the
   number unchanged, byte for byte, except the three rules of item 3. The schema rules of `report.json` (SPEC-0022) move word for word. One plain line under each
   heading says where the rules came from and that a bare `rule N` in that section means the old spec's rule N:

   | Spec | Old rules | SPEC-0011 rules |
   | --- | --- | --- |
   | SPEC-0014 | 1 to 5 | 24 to 28 |
   | SPEC-0015 | 1 to 8 | 29 to 36 |
   | SPEC-0016 | 1 to 10 | 37 to 46 |
   | SPEC-0017 | 1 to 9 | 47 to 55 |
   | SPEC-0019 | 1 to 10 | 56 to 65 |
   | SPEC-0022 | 1 to 12 | 66 to 77 |
   | SPEC-0024 | 1 to 8 | 78 to 85 |
   | SPEC-0026 | 1 to 10 | 86 to 95 |

   SPEC-0011 rules 1 to 23, its header, its tests, proof and residual sections are unchanged.
2. **Each of the eight specs keeps its number and its history.** Its `## Rules` section holds one line per old rule,
   `N. Now SPEC-0011 rule M.`, and nothing else. Its title, status line, opening paragraphs, `## Tests`, `## Proof`,
   `## Residual` and `## Open questions` sections are unchanged, so a citation such as `SPEC-0022 rule 5` or `SPEC-0016 rule 3`
   in a verdict, an ADR, a test or code still resolves through the pointer line. No spec number is reused or deleted.
3. **Where a later spec amended an earlier one, only the amended text moves.** The text that moves is each rule as it stands
   on the default branch, which already holds the in-place amendments (for example SPEC-0022 rules 3 and 7 as SPEC-0024
   amended them), with one change: SPEC-0026 is one of the eight specs and amends SPEC-0022 rules 3, 5 and 7 (its rules 1,
   2, 3, 7 and 9, by proposed spec amendments 46), so those three rules move with that amendment written into them
   (Q-385-6):
   - SPEC-0011 rule 68 (SPEC-0022 rule 3): `schema` is the number 3 since SPEC-0026; the keys are `schema`, `week`,
     `opening`, `sections`, `counts` and `notices`, and no other; a group's `count` is `"unknown"` when the group holds an
     `unknown` item; `counts` has exactly the keys `delivered`, `proven`, `needs_you` and `at_risk`, each counted by meaning
     (SPEC-0026 rule 1) or `"unknown"`.
   - SPEC-0011 rule 70 (SPEC-0022 rule 5): the four kinds that list `entries` also have `count`, the number of their
     entries; `week-totals` also has `fix_verdicts_unknown`, after `fix_verdicts`.
   - SPEC-0011 rule 72 (SPEC-0022 rule 7): `schema` is 3, and a kind or a field not in rule 5 does not exist in schema 3.

   Every other moved rule is byte for byte the text before the move, so SPEC-0011 rules 68, 72 and 92 now agree on
   `schema` 3. The amendment files that amend these specs without being among the eight (for example numbers 55, 58, 66
   and 78 for SPEC-0022 and SPEC-0024, which take `schema` to 7 today) keep applying to the same rules, now found at their
   SPEC-0011 numbers; this proposal does not fold them into the text (Q-385-2).

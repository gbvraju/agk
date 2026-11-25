# Proposed spec amendments 236 (SPEC-0072; REQ-080)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0793 (brief #1918, SPEC-0073 rule 13), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 5). This file proposes the lines and does not edit the spec. SPEC-0073's build (g) applies it word for
word, on the owner's `Maintainer answer: amendment 236 approved`; no session posts it (`Q-PN-2`).

The sentence (brief #1918), quoted as data: "Intake for Day-1 quality: a grill interview tests every idea before its vision, and the same path then holds the product, design, architecture and build to industry practice, in solo and team, with no slower path and no new CI job."

## Items

1. **SPEC-0072 rule 5, the quality sections.** After "a record with none of these sections, written before them, is
   `not run` until its next edit." add: "The record also holds `## Quality scenarios` (one or more per need: stimulus,
   response and its number, named by the quality attributes of ISO/IEC 25010), `## Threats` (each data flow of
   `## Diagram` with its STRIDE threats and the mitigation or the accepted risk) and `## Operations` (what is traced
   and what is alerted, beyond `## Needs`). They are the tuple `QUALITY_SECTIONS`, held apart from the sections above:
   a record with none of them is a note until its next edit, and the sections above and their hold are unchanged
   (amendment 236)."
2. **SPEC-0072 rule 5, the designs comparison.** Add at the end of the rule: "When `[architecture] layers` has more than
   the single default layer `src`, the stack skill compares `[quality] designs` interface designs for each layer and
   keeps the rejected one in the stack ADR outside the `- Option` bullets that `pins.OPTION` and `chosen_services`
   parse (amendment 236)."

No other rule changes.

2026-11-25 (from `date -u`), brief #1952: items 1 and 2 (to rule 5) applied to `docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` word for word, on the maintainer's answer on #1920 (comment 7172944626).

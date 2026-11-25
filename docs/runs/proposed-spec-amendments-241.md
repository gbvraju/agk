# Proposed spec amendments 241 (SPEC-0072; REQ-081)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0794 (brief #1919, SPEC-0074 rule 13), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 5). This file proposes the lines and does not edit the spec. SPEC-0074's build (e), after (b) and SPEC-0073's build (g), applies it word for
word after amendment 236, on the owner's `Maintainer answer: amendment 241 approved`; no session posts it (`Q-PN-2`).

The sentence (brief #1919), quoted as data: "Intake for domain intelligence on the Day-1 quality path: the grill, the glossary, the architecture and review know the customer's business, its rules and its regulations, from cited domain packs and the project's own domain model, confirmed by a person where it matters."

## Items

1. **SPEC-0072 rule 5, domain constraints in the record.** After amendment 236's first item ("... the sections above
   and their hold are unchanged (amendment 236).") add: "Each constraint of the composed domain packs (SPEC-0074 rule 4)
   is one row of `## Quality scenarios`, citing its pack id, and each data flow of `## Threats` carries the data class
   of `docs/domain/data.md` (amendment 241)."
2. **SPEC-0072 rule 5, the stack's domain fit.** At the end of the rule, after amendment 236's second item, add: "With
   `[domain] packs` set, the stack ADR carries after each `- Option <X> — ...` bullet, on its own indented line outside
   what `pins.OPTION` parses, `Domain fit: meets` or `Domain fit: cannot meet: <constraint ids>`; an option that
   cannot meet a hard constraint is shown as such and never hidden or dropped, and a pack's reference notes are offered
   as options, never imposed (amendment 241)."

No other rule changes.

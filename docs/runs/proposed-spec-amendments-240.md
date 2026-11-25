# Proposed spec amendments 240 (SPEC-0048; REQ-081)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0794 (brief #1919, SPEC-0074 rule 13), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0048-a-problem-in-a-person-s-words-takes-one-guided-path-to-the-builds.md` (rule 23). This file proposes the lines and does not edit the spec. SPEC-0074's build (b), after (a), applies it word for
word, on the owner's `Maintainer answer: amendment 240 approved`; no session posts it (`Q-PN-2`).

The sentence (brief #1919), quoted as data: "Intake for domain intelligence on the Day-1 quality path: the grill, the glossary, the architecture and review know the customer's business, its rules and its regulations, from cited domain packs and the project's own domain model, confirmed by a person where it matters."

## Items

1. **SPEC-0048 rule 23, domain packs compose after the playbook.** After "and the no-weakening check of rule 21 reads
   them by id (`Q-S0048-25`)." add: "The domain packs of SPEC-0074 (`config/domains/<slug>.toml`) compose after the
   playbook and its modules, in the order of `[domain] packs`, then the project's own pack: `default`, the work type,
   its modules, each pack, the project's pack, each item once at its first place. A later layer's gate with an earlier
   id replaces it only when it is the same or stronger, and a weakening is refused naming the key, as rule 21 says. A
   jurisdiction layer is a pack whose `domain` is `<domain>-<region>` and composes right after its domain. Where two
   composed regulations constrain the same attribute differently, the stricter holds until a person decides; the
   composer prints both sources and never chooses (amendment 240)."

No other rule changes.

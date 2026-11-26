# Proposed spec amendments 258 (SPEC-0029; REQ-083)

Date: 2026-11-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0834 (brief #2017, SPEC-0076 rule 14), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0029-a-product-owner-starts-from-a-brief-idea-the-vision-the-stac.md` (rule 5). Amendment 256 is the newest on main and open briefs name 254, 255 and 257 (#2015), so this intake
proposes 258 to 260 (`Q-S0076-8`). This file proposes the lines and does not edit the spec. SPEC-0076's build (c), after (a),
applies it word for word, on the owner's `Maintainer answer: amendment 258 approved`; no session posts it.

The sentence (brief #2017), quoted as data: "Intake for the parts list: after the stack is accepted and before the foundation, each library a product uses is chosen per need from a cited catalogue, recorded with its reason, alternatives and health, explained in plain words, and kept in step with every build file and lock."

## Items

1. **SPEC-0029 rule 5, the platform only in `Parts:`.** Replace "for the runtime, the framework, the database engine and
   each library it names," with "for the runtime, the framework and the database engine,", and after "and an Accepted
   record is checked as before." (the second time it appears) insert: "Libraries are not named in `Parts:`: each
   library is chosen per need in the parts record `docs/parts.md` (SPEC-0076 rule 2); an Accepted record whose `Parts:`
   names libraries stays valid, and those libraries are harvested into the parts record as `inferred` rows
   (amendment 258)."
   Class: behaviour

No other rule changes.

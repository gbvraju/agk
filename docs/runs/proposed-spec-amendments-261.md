# Proposed spec amendments 261 (SPEC-0029; REQ-084)

Date: 2026-11-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0837 (brief #2022, SPEC-0077 rule 13), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0029-a-product-owner-starts-from-a-brief-idea-the-vision-the-stac.md` (rules 1 and 2). This file proposes the lines and does not edit the spec. SPEC-0077's build (e), after (c),
applies it word for word, on the owner's `Maintainer answer: amendment 261 approved`; no session posts it.

The sentence (brief #2022), quoted as data: "Intake for market packs and evaluations: AGK keeps a small stable core and reads its stack, language, library, domain and pattern knowledge, and its skills, from pinned, scanned, dated packs, and promotes a pack or a release only when reference products score as well or better."

## Items

1. **SPEC-0029 rule 1, an engine from a pinned pack.** After "A value is the name of a skill the session can see;"
   insert " a value may also be `<pack id>:<skill>`, a skill of a pack that `[packs] use` lists and `config/packs.lock`
   holds (SPEC-0077 rules 4 and 12, amendment 261);".
   Class: behaviour
2. **SPEC-0029 rule 2, its doctor line.** After "or `missing` (named but not found)." insert " A `<pack id>:<skill>`
   value of a pack in use is reported the same way, from the pack's folder that the lock verifies, never
   `plugin-unreadable`; a prefix that names no pack in use stays `cannot-check` `plugin-unreadable` (amendment 261)."
   Class: behaviour

No other rule changes.

# Proposed spec amendments 260 (SPEC-0054; REQ-083)

Date: 2026-11-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0834 (brief #2017, SPEC-0076 rule 14), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0054-every-dependency-is-scanned-and-listed-in-a-standard-bill-of-materials.md` (rules 2 and 3). Amendment 256 is the newest on main and open briefs name 254, 255 and 257 (#2015), so this intake
proposes 258 to 260 (`Q-S0076-8`). This file proposes the lines and does not edit the spec. SPEC-0076's build (f), after (d),
applies it word for word, on the owner's `Maintainer answer: amendment 260 approved`; no session posts it.

The sentence (brief #2017), quoted as data: "Intake for the parts list: after the stack is accepted and before the foundation, each library a product uses is chosen per need from a cited catalogue, recorded with its reason, alternatives and health, explained in plain words, and kept in step with every build file and lock."

## Items

1. **SPEC-0054 rule 2, a component's purpose.** After "elsewhere it is refused as a file the bill reads (amendment
   232)." insert: "Where the commit holds a parts record (`docs/parts.md`, SPEC-0076 rule 7), each `python` or `node`
   component that a row of the record names carries that row's need as its purpose; a component no row names carries
   none, and the bill never guesses one (amendment 260)."
   Class: behaviour
2. **SPEC-0054 rule 3, the purpose property.** Replace "and the properties `agk:class` and, for an unpinned component,
   `agk:pin`." with "and the properties `agk:class`, for an unpinned component `agk:pin`, and, for a component a row of
   the parts record names, `agk:purpose` with that row's need id (amendment 260, `Q-S0076-11`)."
   Class: behaviour

No other rule changes.

2026-11-28 (from `date -u`), brief #2073: items 1 and 2 (to rules 2 and 3) applied to `docs/specs/0054-every-dependency-is-scanned-and-listed-in-a-standard-bill-of-materials.md` word for word, on the maintainer's answer on #2018 (comment 7227145482).

# Proposed spec amendments 262 (SPEC-0074; REQ-084)

Date: 2026-11-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0837 (brief #2022, SPEC-0077 rule 13), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0074-the-day-1-quality-path-knows-the-customer-s-domain.md` (rules 3 and 12). This file proposes the lines and does not edit the spec. SPEC-0077's build (j), after (b)
and (h), applies it word for word, on the owner's `Maintainer answer: amendment 262 approved`; no session posts it.

The sentence (brief #2022), quoted as data: "Intake for market packs and evaluations: AGK keeps a small stable core and reads its stack, language, library, domain and pattern knowledge, and its skills, from pinned, scanned, dated packs, and promotes a pack or a release only when reference products score as well or better."

## Items

1. **SPEC-0074 rule 3, the seed packs as their own pack.** Replace "The packs ship in the kit, versioned with its
   releases; a later brief may move them to their own plugin." with "The packs ship in the kit, versioned with its
   releases, until SPEC-0077's build (j) moves them to their own curated pack (SPEC-0077 rule 3), a plugin of the kit's
   marketplace versioned on its own, which a project pins in `[packs] use`; that move is promoted only by an eval record
   the person accepted (SPEC-0077 rule 10) (amendment 262)."
   Class: behaviour
2. **SPEC-0074 rule 12, a domain pack from a pinned pack.** In the `packs` row of the settings table, replace "a list of
   pack names, each a shipped pack or a project pack under `config/domains/`" with "a list of pack names, each a shipped
   pack, a domain pack of a pack in use (SPEC-0077 rule 5) or a project pack under `config/domains/` (amendment 262)".
   Class: behaviour

No other rule changes.

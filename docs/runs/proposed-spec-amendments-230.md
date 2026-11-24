# Proposed spec amendments 230 (SPEC-0072; REQ-079)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0784 (brief #1890), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 8). This file
proposes the lines and does not edit the spec. A later pull request applies them word for word, on the owner's
`Maintainer answer: amendment 230 approved`; no session posts it.

The sentence (brief #1890): "A TypeScript product with the stock typescript-eslint config meets the Node pack's lint
floor: a floor rule typescript-eslint turns off is met by its replacement rule or, in a file a strict tsconfig.json
checks, by the compiler, from a fixed table; no rule is dropped."

## Items

1. **Rule 8, the second bullet ("Teams may define, or not").** Replace "is accepted only when the pack's `floor` step
   shows that it enables every rule code of the pack's `rules` list (`Q-S0072-14`)" by "is accepted only when the
   pack's `floor` step shows that it enables every rule code of the pack's `rules` list, or meets it by the equivalent
   the pack's fixed table names (a companion config's replacement rule, or the compiler for a file a strict compiler
   configuration checks; amendment 230) (`Q-S0072-14`)". The rest of the bullet is unchanged: every code stays
   judged, so `Q-S0072-14`'s "may add rules and never disable one" holds.

No other rule changes.

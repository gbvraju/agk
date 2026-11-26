# Proposed spec amendments 250 (SPEC-0072; REQ-082)

Date: 2026-11-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0807 (brief #1948, SPEC-0075 rule 13), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0072-each-work-type-playbook-carries-its-architecture-a-stack-sta.md` (rule 5). This file proposes the lines and does not edit the spec. SPEC-0075's build (c), after (a), applies it word for
word after amendment 207 (ADR-0677) and amendment 236, on the owner's `Maintainer answer: amendment 250 approved`; no
session posts it. If amendment 207 is not yet applied when build (c) starts, the build asks with a `Question:` and
changes nothing in the spec.

The sentence (brief #1948), quoted as data: "Intake for the data model on the Day-1 quality path: every project with stored data gets an expert, engine-aware database design from its domain model, curated and cited patterns and its main queries, confirmed by a person on business choices, checked offline and kept in step with each migration."

## Items

1. **SPEC-0072 rule 5, the data model's sections and classes.** After amendment 207's text on `docs/data-model.md` add:
   "The data model holds `## Business view`, `## Logical model`, `## Physical model` (one `### <store>` per store of
   `## Data stores`, in its engine profile's form), `## Main queries` and `## Lifecycle` (SPEC-0075 rule 2), and
   `## Data stores` names each store's subsection. The data class of each item is read from `docs/domain/data.md`
   (SPEC-0074 rule 7); a record written with the classes `none`, `contact` and `sensitive` maps `none` to
   `public`, `contact` to `personal`, and `sensitive` to `health`, `payment` or `confidential` by the
   person's yes, and is held as an open point until then (amendment 250)."

No other rule changes.

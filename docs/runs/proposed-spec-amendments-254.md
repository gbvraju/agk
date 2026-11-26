# Proposed spec amendments 254 (SPEC-0030; REQ-037)

Date: 2026-11-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0828 (brief #2002), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0030-a-conductor-role-reviews-every-pull-request-posts-the-verdic.md` (rules 4 and 6). Brief #2002 reserved
amendment 254. This file proposes the lines and does not edit the spec. They are applied word for word, on a person's
`Approve: SPEC-0030`; no session posts it.

## Why

Of the 40 most recently merged pull requests (#1845 to #1984), 14 asked the owner at merge about a build against its
Approved spec or its brief, about 31 hours of owner wait; nine of those amendments were already reserved at filing.

## Items

1. **SPEC-0030 rule 4, the shape of a brief.** After "and exactly one line `Size: S`, `Size: M` or `Size: L`." insert "For each Approved spec its Answers name, or whose `Requirements:` line names a requirement of its `Advances:`, one line `Spec fit: SPEC-<nnnn> <part>[; <part>]`, each part `rule(s) <list> within` or `rule(s) <list> change by amendment <n>`, naming every rule of that spec the brief names; a change carries the amendment's items quoted under its line and `Reserved:` names the amendment (amendment 254)."
Class: behaviour
2. **SPEC-0030 rule 6, the conductor.** After the sentence on the verdict comment insert "A departure from an Approved rule that the brief's `Spec fit:` line states within, or from the brief where brief and spec agree, is a fix list item to follow the approved text, never an owner ask; an amendment the brief's issue approved for the text at the head is not asked again (amendment 254)."
Class: behaviour

No other rule changes.

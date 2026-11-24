# Proposed spec amendments 238 (SPEC-0063; REQ-080)

Date: 2026-11-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0793 (brief #1918, SPEC-0073 rule 13), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0063-in-team-mode-every-listed-reviewer-may-run-a-steward-first-come-first-served.md` (rules 3 and 5). This file proposes the lines and does not edit the spec. SPEC-0073's build (d) applies it word for
word, on the owner's `Maintainer answer: amendment 238 approved`; no session posts it (`Q-PN-2`).

The sentence (brief #1918), quoted as data: "Intake for Day-1 quality: a grill interview tests every idea before its vision, and the same path then holds the product, design, architecture and build to industry practice, in solo and team, with no slower path and no new CI job."

## Items

1. **SPEC-0063 rule 3, routing by area.** After the bullet **Routing by area.** add: "A grill item of SPEC-0073 names its
   area (`product`, `design` or `architecture`); an area maps to a path class of `config/reviewers.yaml`: `architecture`
   to that class's approvers, `product` and `design` to `spec_approvers` until named roles exist, and an item outside
   the asking reviewer's area is posted as `Question: Q-<id> for the maintainers: <plain sentence>` on the problem issue
   and routed so (amendment 238)."
2. **SPEC-0063 rule 5, the lapse in discovery.** Add at the end of the rule: "A grill item still untaken or unanswered
   past `[flow] owner_wait_minutes` (counted outside `owner_rest_hours`) stays a `D-<n>` open point and the grill goes
   on; a risk on it is accepted only by a reviewer of its area in their own words, and a critical `problem`, `success`
   or `non-goals` risk only by a `spec_approvers` login (amendment 238)."

No other rule changes.

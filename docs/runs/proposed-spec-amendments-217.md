# Proposed spec amendments 217 (SPEC-0037; REQ-044)

Date: 2026-11-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0734 (brief #1756), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md` (rule 3). Brief #1756 reserved the
number 217. This file proposes the lines and does not edit the spec. A later pull request applies them word for word,
on the owner's `Maintainer answer: amendment 217 approved`, as on #1555; no session posts it.

The sentence (brief #1756): "On the path from an idea, the screen list is drawn from the accepted charter's milestones
and the discovery answers, and a screen list with no screen is refused when discovery says the work has screens."

## What is on the default branch today

Read in the code on main at b4a865c9 (2026-11-22): `design.py inventory` writes one section per requirement of
`docs/requirements.md`. On the path from an idea that file holds only the kit's requirements before `/agk:plan-intake`,
so the skeleton has no slot to fill, every section reads `no screen: a rule of the kit`, and `check_design.py` prints
`ok design` although the discovery document says `- Screens: yes`.

## Items

1. **Rule 3, after "with its slots empty."** Add: "On the path from an idea, when `docs/requirements.md` holds no
   product requirement (none from REQ-101 up) and an Accepted charter ADR (`docs/adr/<n>-project-charter.md`) is
   present, the skeleton also holds one section for each milestone of the newest Accepted charter, headed
   `M<n> — <the milestone line>`, whose `- Sources:` line names the charter and each discovery document of
   `docs/discovery/` whose `Screens` is `yes` or `open`, with its Screens slot empty; the session fills those
   slots from the charter and those documents, and from nothing else. A charter with no Milestones item is refused,
   naming the path class `docs/adr/`. A charter that is still Proposed is not a source. With a product requirement
   present the skeleton is as before, and a signed-off inventory stays as signed when the plan's requirements land
   later: a requirement section is added only by a new inventory pull request (amendment 217)."
2. **Rule 3, at its end.** Add: "`check_design.py` also fails an inventory that lists no screen while a discovery
   document says `Screens: yes` or `Screens: open` outside its quoted blocks, naming this rule and the path class
   `docs/design/`; with every discovery document at `Screens: no`, or none, an inventory with no screen passes
   (amendment 217)."

No other rule changes.

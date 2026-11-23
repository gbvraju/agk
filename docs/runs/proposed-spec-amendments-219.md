# Proposed spec amendments 219 (SPEC-0037; REQ-044)

Date: 2026-11-23 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0745 (brief #1779), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md` (rules 3 and 15). Brief #1779 reserved
the number 219. This file proposes the lines and does not edit the spec. A later pull request applies them word for
word, on the owner's `Maintainer answer: amendment 219 approved`; no session posts it.

The sentence (brief #1779): "On the path from a customer's prototype, the screen list starts from the imported pages,
so each page maps to a screen and the prototype's text reaches the plan; a map that marks every page out while no
screen exists is refused."

## What is on the default branch today

Read in the code on main at ee47218b (2026-11-23): `design.py inventory` writes one section per requirement of
`docs/requirements.md` and, since amendment 217, one per milestone of an Accepted charter. A project that starts from a
customer's prototype has neither, so its inventory has no screen. In a sample project with a five-page import the only
map `check_design.py` accepted marked every page `out` (`ok design`), and `design_import.py source` then wrote a source
of 0 headings: none of the customer's page text reached the plan.

## Items

1. **Rule 3, after the sentence amendment 217 adds about the idea path.** Add: "On the path from a customer's
   prototype, when `docs/requirements.md` holds no product requirement (none from REQ-101 up) and an imported version
   of rule 15 is present, a new skeleton also holds, in its Screens part, one `### <page slug>` section for each page
   and picture page of the `pages` list of the newest imported version's `manifest.json`, the slug made from the
   file's name (lower case, every run of other characters one `-`, `-2`, `-3` added to a slug already used), with a
   `- Sources:` line naming the page's file under that version and every other slot empty; the session fills those
   slots from those pages, and from nothing else, and the version's map then names those screens. Only the newest
   imported version is a source. An existing inventory is only appended to as before. With a product requirement
   present the skeleton is as before (amendment 219)."
2. **Rule 15, at its end.** Add: "`check_design.py` fails, naming this rule and the path class
   `docs/design/imported/`, when every row of an imported version's `map.md` is `out:` while the inventory lists no
   screen, or there is no inventory; with a screen in the inventory, a page may still be mapped `out:` with a reason
   (amendment 219)."

No other rule changes. `docs/guides/planning.md` step 1 says that on a new project the inventory may come from the
import.

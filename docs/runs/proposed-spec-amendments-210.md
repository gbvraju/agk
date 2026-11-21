# Proposed spec amendments 210 (SPEC-0037; REQ-044, REQ-079)

Date: 2026-11-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0681 (brief #1601, reserved number 210), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md` (rule 11). SPEC-0072 rule 10 asks
for this proposal from its build (h). This file proposes the lines and does not edit the spec; they apply on the spec
approver's `Approve: SPEC-0037`, and a later build adds the check; no session posts the approval.

## What is on the default branch today

Read in the code by this session on main at 4dceb89 (2026-11-21):

- SPEC-0037 rule 11 holds a UI build to the signed-off version through `design_compare.py`, which compares the
  rendered structure, tokens and pixels; no rule says whether the prototype's markup may be copied into production.
- SPEC-0072 rule 10: "a signed-off prototype is a reference only: a UI build takes its structure, states and tokens
  and writes production markup in the stack's components, and `design_compare.py` compares the rendered result, never
  the markup."

## Items

1. **Rule 11, one sentence added at its start.** "A signed-off prototype is a reference only: a UI build takes its
   structure, states and tokens and writes production markup in the stack's own components, never a copy of the
   prototype's pages; `design_compare.py` compares the rendered result, never the markup (SPEC-0072 rule 10)."
2. **Rule 13, one clause added.** "No production file of a UI build copies a page of `docs/design/prototype/`."
3. **The build.** A check that refuses a UI build whose production files under `ui_paths` repeat a prototype page's
   markup, naming the rule and the screen, never a value; filed later by the `brief` skill, tests first, after the
   approval.
4. **Unchanged:** every other rule of SPEC-0037, `design_compare.py`'s three comparisons and `config/review-checklist.md`
   (SPEC-0072 rule 10, `Q-S0072-1`).

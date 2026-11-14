# Proposed spec amendments 173 (SPEC-0037; REQ-044)

Date: 2026-11-14 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0512 (brief #1208), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md`. Brief #1208 reserved ADR-0512 and no
amendment number; 173 is the next free one on the default branch (172 is the highest there). The amendment line is
applied under rule 7 in the same pull request, as the brief's answer 3 asks. The owner decides it with
`Approve: <head> SPEC-0037` on the pull request; no session posts that line.

The sentence (brief #1208): "Only the latest kit version of a design must cover the current inventory, so a screen added
after a signed-off version does not fail that frozen version forever."

## What is on the default branch today

Read in the code by this session on `origin/main` (cdb4e38):

- `scripts/agk/check_design.py` `cmd_check` calls `design_prototype_check.version_problems(root, version)` for every
  kit version that `design_prototype_check.versions` lists, and each one fails `the state has no page` for every `yes`
  state of the current `docs/design/inventory.md` that it lacks (rule 7).
- `scripts/agk/design_signoff.py` `frozen_problems` fails any change in a signed-off version's folder (rule 9), so an
  older signed-off version that predates a screen can never gain its page.

## Items

1. **Rule 7, one amendment line.** "The coverage of the inventory (a `yes` state with no page) applies to the latest kit
   version only, the highest-numbered `v<n>`; an older version keeps every other check of this rule and rule 9's frozen
   digest, a page of it for no screen fails only while it is not signed off, and an older version that lacks a state
   reads `design: v<n> predates the inventory; v<m> is the version checked for coverage`, information only."
2. **No other change.** Rules 5, 6, 8 and 9, the imported versions of rule 15 and every workflow stay as they are.
3. **Tests.** `tests/kit/test_check_design_prototype.py`: a signed-off `v1` with a `v2` that covers a screen added after
   it passes with the note; the latest version lacking a state fails; a single version is checked as before with no note;
   an older complete version prints no note; an older page for a removed screen fails unsigned and passes signed off; a
   signed-off older version still fails rule 9 on a change.

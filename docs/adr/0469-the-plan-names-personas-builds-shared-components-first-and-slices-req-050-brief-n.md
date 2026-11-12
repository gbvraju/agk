# ADR-0469: The plan names personas, builds shared components first, and slices each milestone for a demo

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0037, SPEC-0038, ADR-0269, ADR-0454, amendment 163, amendment 164, brief #1089, plan #661
- Requirements: REQ-050, REQ-044

## Context

The owner wants the plan to understand reusable components and personas, so that development shows visible outcomes in
agile steps (brief #1089). SPEC-0043 (Approved, REQ-050, ADR-0269) drafts a plan from `docs/sources/` as proposals, but its
requirements name no user, its milestones have no screens, and nothing in it or in SPEC-0037 finds what repeats across an
imported prototype's pages. The inventory (SPEC-0037 rule 3) already gives each screen its pattern and states, the web-app
playbook already orders batches by demo value (SPEC-0038 rule 7), and `design_compare.py` already proves a built screen
against a signed-off version (SPEC-0037 rule 11). Amendment 163 (ADR-0454) makes the imported prototype a `Kind: design`
source and orders Wave 7's builds.

## Decision

1. The proposals gain `personas`, each with goals and sources, and each requirement names its persona and one story
   `As <name>, I want ..., so that ...`; `validate` refuses a requirement without a known persona and a persona without
   sources, and a user the sources only imply is an open question with `(verify)`. `render` writes
   `docs/plan/personas.md` and `Persona:` and `Story:` lines, and the trace gains a persona column (amendment 164 item 2).
2. `design_import.py components --version i<n> --slug <slug>` writes once a `Kind: design` source listing each element
   structure that two or more mapped pages share, by tag, class names and child tags, never page text, and nothing is
   run or opened (a new SPEC-0037 rule 16; rule 13's exception covers that file). The proposals gain `components`, each
   one brief of `M1 Foundation`, and `validate` refuses a screen brief that does not depend on the brief of a component
   its screens use (item 3).
3. Every milestone after `M1` lists the inventory screens and states it makes demoable, its exit says each reads `match`
   in `design_compare.py` against the signed-off version, and the milestones follow the playbook's `batch_by`; `validate`
   refuses, when a design source exists, a later milestone without screens and a source screen and state that no
   milestone lists. `render` prints a `Demo:` line, and the review output lists each screen's comparison line as its
   evidence (item 4).
4. The builds run (p) personas, after #1081 and #1076; (q) component detection, after #1077; (r) components and slices,
   after (p) and (q); then SPEC-0043's (e) to (h), (e) after #1075 and (h) also after (r). None changes a rule of Wave 7's
   builds (item 5).

## Consequences

A plan drafted from a prototype says who each requirement serves, builds what the screens share first, and ends each
later milestone with screens a person can click through and that are proved against the signed-off design. A plan with
no design source keeps rule 4's milestones. This pull request changes documents only: no code, no test, no workflow and
no protected path class. Each build of item 5 writes its own ADR naming the protected classes it changes, after the
owner's `Approve: <head> SPEC-0043` and `Approve: <head> SPEC-0037` on this pull request.

## Residual

- 2026-11-12: structure matching misses a component written in different markup and may list a repeated structure that
  is not one; the person edits `components` before `render` (due 2026-12-31).
- 2026-11-12: a customer's class names enter `docs/sources/`, without page text; the guard of SPEC-0043 rule 3 scans the
  file (due 2026-12-31).
- 2026-11-12: the brief fields, the dependence rule, the story form, the component rule and the screens to cover are the
  owner's (`Q-1089-2` to `Q-1089-6`) (due 2026-11-30).

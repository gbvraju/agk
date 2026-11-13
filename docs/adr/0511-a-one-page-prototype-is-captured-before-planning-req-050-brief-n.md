# ADR-0511: A one-page prototype is captured before planning

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: SPEC-0037, SPEC-0043, ADR-0472, ADR-0473, brief #1204, plan #661
- Requirements: REQ-050

## Context

`/agk:design import` treats each HTML file as one page. A prototype that is one `index.html` whose screens a script
draws imports as one page: its `map.md` has one row and `design_import.py source` reads almost no screen text. The
inventory is written from the requirements and the specs alone (SPEC-0037 rule 3), so a plan can be approved with full
scenario coverage while product screens of the prototype have no inventory screen. In a trial, four such screens were
found only by a comparison by hand after the approval: nothing told the person that a one-page import cannot be compared.

## Decision

1. `scripts/agk/design.py import`, after a successful import, prints one line when the new version has exactly one HTML
   page and that page holds a `<script` element: `notice: i<n> has one page drawn by script; capture each screen and
   state as its own page and import that folder instead (docs/guides/planning.md "From a prototype")`. The exit stays 0.
   The page is read as bytes only: nothing is run and no network is used.
2. `docs/guides/planning.md`, "From a prototype and an OpenSpec file", gains a step 0: a prototype drawn by script is
   first captured as one HTML file per screen and state, named `<screen>--<state>.html`, with any headless browser the
   person has (the kit installs none), and that folder is imported. The plan is approved only after
   `check_plan.py --trace` has run with the prototype source, so its `unmatched screen:` lines are read before approval.
3. `skills/plan-intake/SKILL.md`: when `docs/design/imported/` has no version with more than one page and the sources
   hold no `Kind: design` file, the skill says so to the person before drafting and points at step 0.

## Consequences

A one-page prototype drawn by script is flagged at import instead of passing silently, and the guide orders capture,
import and trace before approval. The notice is information, not a failure: no check changes. `tests/kit/test_design_import.py`
checks the notice (once, exit 0), its absence for a one-page import without a script and for a two-page import, the
guide's step 0 and the skill's sentence. Protected path classes changed: `scripts/agk/` (`design.py`), `skills/` (the
plan-intake skill) and `tests/kit/` (the tests). No workflow changes.

## Residual

- 2026-11-13: the notice reads only a `<script` element; a single page drawn by CSS alone, or one page with several
  scripted states beside other pages, is not flagged; the maintainers may widen it (due 2026-12-31).

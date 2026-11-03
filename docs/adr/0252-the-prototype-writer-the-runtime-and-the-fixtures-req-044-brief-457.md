# ADR-0252: the prototype writer, the kit's runtime and the fixture set (REQ-044, brief 457)

- Status: Proposed
- Date: 2026-11-02
- Deciders: maintainers
- Related: ADR-0204, ADR-0248, ADR-0249, SPEC-0037
- Requirements: REQ-044

Protected classes: `kit/`, `scripts/agk/`, `skills/`, `tests/kit_dev/`

## Context

SPEC-0037 (Approved; ADR-0204) has a design phase deliver a click-through prototype (rules 4 to 6), drawn only from an
agreed inventory (rule 3) and carrying an existing theme over (rule 12). Brief #457 is build (c) of rule 14, after the
standard (#455, ADR-0248) and the inventory and sign-off record (#456, ADR-0249). The person ruled on 2026-10-30 that
the prototype uses the kit's own small, hashed, offline navigation runtime with a state bar and demo mode on every
screen (ruling 1), and that v1 is regenerated from the inventory with the theme carried over (ruling 3). ADR-0204
decision 3 names the classes the builds change; this ADR names the ones this build changes, because the protected-path
check counts only an ADR of the same pull request (`Q-S0037-9`).

## Decision

1. **The kit's prototype folder (answer 1).** `kit/templates/design-prototype/` holds `page.html` and `index.html` (the
   page shells: `lang`, the viewport line, `standard.css` and `theme.css` of the folder, one
   `<script src="agk-prototype.js"></script>` at the end, and `data-density`/`data-align` on `<html>` for the theme's
   layout block), `agk-prototype.js`, `fixtures.json` and `README.md`. `agk-prototype.js` starts `// agk-prototype 1`;
   it reads only the page's own links and the `data-demo` attribute of its demo links; it gives the state bar keyboard
   access (arrow keys, Home and End inside the bar, digits 1 to 9 anywhere) and a demo mode (d on or off; n or the right
   arrow for the next step and p or the left arrow for the previous one; the presenter's sentence shown), carried from
   page to page only by the `#demo` fragment of the address. Its text holds none of the request names of answer 1, in
   any case, and no `http`, `innerHTML`, `eval(` or `document.cookie`. It is kept byte-stable after this build: #458
   lists its hash.
2. **The fixtures (answer 2).** `fixtures.json` holds invented people, organisations, addresses, amounts, dates, items,
   metrics, notices, phone numbers, and email addresses and links on `example.com`, `example.org` or `example.net` only,
   with long values for `long-content`; it fills every `{{<group>.<key>}}` slot of `kit/templates/design-patterns.md`
   except `link.*` (pages of the folder) and `page.title` (the screen's title from its inventory id).
3. **The writer (answer 3).** `scripts/agk/design_prototype.py` (new, kit-only, listed with the kit-only scripts of
   `tests/kit_dev/test_kit_manifest.py`; `kit/manifest.json` is unchanged) and `design.py prototype [--root DIR]` write
   the next free `docs/design/prototype/v<n>/` (the highest existing `v<n>` plus one; `Q-S0037-4`): `index.html`, one
   `<screen>--<state>.html` for each screen and each state marked `yes`, `standard.css` and `agk-prototype.js` copied
   byte for byte, `theme.css` (the theme block), `demo.md` and `README.md`. A page is the pattern's block for its state
   (the `default` block for a state the standard does not name), its slots filled from `fixtures.json` alone and
   HTML-escaped, with one `h1` (the block's own, else the screen's title), a state bar of plain relative links to every
   page of the screen, plain relative links to each screen of `- Links to:`, and on a demo step plain `rel="prev"` and
   `rel="next"` links and the `data-demo` sentence. A flow's demo path is one step per screen of the flow with a page,
   in the inventory's order, at its `default` page. Everything is built in memory before the first write, and a folder
   is never overwritten.
4. **The refusal of AC2 (answer 4).** `design.py prototype` refuses, `rule 3: the inventory has no inventory row in
   docs/design/signoffs.md for its digest`, when `design_signoff.inventory_digest` matches no `inventory` row of
   `design_signoff.rows`; it also refuses, naming rule 3, an inventory that does not exist or does not pass
   `design_inventory.inventory_problems`. No refusal names a digest or a value, and nothing is written.
5. **The theme (answer 5).** `kit/templates/design-theme.md` becomes the standard format of #455 (`Standard: agk design
   standard 1`, Brand with a logo line, one theme block, a layout block, Rules, Evidence). With no theme the writer
   writes it with `{{evidence}}` set to the version. An old-format theme is moved: its five tokens map by
   `design_standard.OLD_TOKENS` to their roles unchanged in value, in light and dark. The owner's title, the text
   before the first section and every section but Tokens, Contrast and Rules stay unchanged and in place, with the
   `Standard:` line added under the title; Tokens becomes the theme and layout blocks, Rules the template's rules, and
   Contrast goes (the standard computes it); a standard section the old theme lacks is the template's, with the
   evidence set to the version. The template's placeholder logo line is added to Brand when the record has none, after
   its last list line or at its end (the standard's check requires one; it reads as a placeholder at risk). An old
   theme that already has a Theme or Layout section, or a section twice, is refused naming rule 2 ("move it by hand"). An old token
   block with any other declaration or rule is refused naming rule 2, nothing guessed. A theme already on the standard
   is never changed, and is refused naming rule 2 when it does not pass `design_standard.standard_theme_problems`.
6. **No new mockup folder (answer 6).** `design.py write` refuses with `rule 12: a new mockup folder is not written; use
   /agk:design prototype` and writes nothing; `design.py screenshots --folder` for existing mockup folders is
   unchanged. `skills/design/SKILL.md` replaces its write step by the prototype step and its argument hint by
   `prototype | inventory`, and says that `screenshots/` is written only by `design.py screenshots`.
7. **Tests first (answer 7)** in `tests/kit_dev/test_design_prototype.py`; `tests/kit_dev/test_design_write.py` changes
   to the refusal (its screenshot tests build an existing mockup folder by hand); `tests/kit_dev/test_pr_bodies_kit.py`
   writes the theme by hand instead of calling `design.py write`. One fragment, `changelog.d/design-prototype.md`
   (answer 8); no version bump; `kit/hashes.json` untouched.

## Consequences

A project with an agreed inventory gets a prototype that a stakeholder can click through from the files, every screen
and state with a state bar, and a presenter's path per flow; a project with an old theme moves onto the standard without
a colour changing. Nothing checks the folder yet: the runtime hash, the fixture check, links and accessibility are
#458's, screenshots and reflow #461's. `/agk:design <name>` no longer makes mockups.

## Residual

- 2026-11-02: `docs/guides/reference.md` still describes `/agk:design` as writing a mockup folder; it is outside this
  brief's `Touches:` line, and a later build (#458 or #461) updates it.
- 2026-11-02: the presenter's sentences are written by the script from the inventory (screen, pattern, flow and links),
  so they are plain; a person who wants other words changes the inventory or, before sign-off, `demo.md` and the pages
  of an unsigned version.
- 2026-11-02: `kit/templates/design-index.html` and `kit/templates/design-readme.md` are no longer written by any
  command; they stay because the tests of existing mockup folders build from them.

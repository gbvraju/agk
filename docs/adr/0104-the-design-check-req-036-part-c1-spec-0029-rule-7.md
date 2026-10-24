# ADR-0104: the design check (REQ-036 part c1, SPEC-0029 rule 7)

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0097, ADR-0099, ADR-0101, ADR-0103
- Requirements: REQ-036

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0029 (Approved, #166) splits its build into (a) engines and doctor, (b) vision and stack (both merged) and (c) design. Part (c) measured, before it was built, about 1,000 changed lines (the check and its tests about 700, the
writer, templates, skill and screenshots about 300), so rule 9 splits it again: (c1) the check, here, and (c2) `/agk:design` with its templates and screenshots, a separate pull request after this one is merged. The tests were written
first (`tests/kit_dev/test_check_design.py`; on unchanged `main`: 39 failed, the script being absent). This pull request branches from the default branch and does not stack on lane A's open #172 (ADR-0102 is that build's), so this ADR
takes 0104.

## Decision

1. **The script** (kit-only, `scripts/agk/check_design.py`; files only, no network, no model, nothing written): with no `docs/design/theme.md` and no mockup folder it prints `ok design (no design record)`.
2. **The mockup** (rule 7): for each folder of `docs/design/mockups/`, the name is `<YYYY-MM-DD>-<name>`, `index.html` and `README.md` exist, and the page has no `<script>`, no event-handler attribute and no `javascript:`; makes no external request
   (no `://`, no `//` source, no `@import`, no `<link>`, `<iframe>`, `<object>`, `<embed>` or `<base>`); has exactly one `<style>` element holding one token block (one `:root` rule, and at most one `:root` rule inside
   `@media (prefers-color-scheme: dark)`, with a light and a dark set); writes no colour outside the token block (a hex, `rgb()`, `hsl()` or similar literal anywhere in the style or in a `style` attribute, or a named colour in a colour property;
   `var()`, `inherit`, `transparent` and `currentColor` pass); and every contrast pair has at least 4.5:1 in both modes.
3. **The theme** (rule 7): the Brand section lists values as `- <key>: <value> — source: <text>` and a value with no source fails; the Tokens section holds one `css` block of the same shape; the Contrast section lists pairs `- --fg on --bg` (default: `--fg`
   on `--bg` and `--muted` on `--bg`), each token a hex colour, the ratio the WCAG 2 contrast ratio computed from the relative luminance; the Evidence section has `Evidence: docs/design/mockups/<folder>/` and the folder exists.
4. **Information, not failure**: when the evidence folder's `README.md` has no line `Approved by <name> on <YYYY-MM-DD>`, the check prints `design: the theme is not approved yet`; when a brand value holds a `[bracketed]` placeholder, it prints
   `at risk design: placeholder brand`. Both come before `ok design`, in that order. The weekly report's At risk section does not read this line yet: see the residual.
5. **Messages** name the rule (`rule 7`) and a path or a token name, never a colour, an address or a brand value.
6. **The governance test** (`tests/kit/test_agk_mk.py`): it requires every `scripts/agk/check_*.py` in the `agk-governance` target and already exempts the kit-only `check_release.py`; it now exempts `check_design.py` the same way, with a comment that names this ADR. This is the one place a test
   is loosened, and it is named here so that the maintainers decide it: the alternative is a governance step, which changes `Makefile`, `agk.mk`, the workflow and the manifest (see the first residual).
7. **No governance step, no default engine, no version bump** (flow mode, SPEC-0028): one line under Unreleased in `CHANGELOG.md`; `check_design.py` is a plugin file (listed as kit-only in the manifest test), so no installed file changes.

## Consequences

- A mockup that cannot be opened offline, that runs code or that uses a colour that is not a token fails before an owner is asked to approve it.
- The owner's approval stays a line the owner writes in the mockup's `README.md`; no check writes it.

## Residual

- 2026-10-24: the check is not a governance step, and `check_design.py` is exempt from "every check is in agk-governance" in `tests/kit/test_agk_mk.py` for (c1) only (Q-K4-261, ruled on #174): (c2) adds the governance step, with its own ADR that names the protected classes it touches (`Makefile`, `agk.mk`, the workflow, the manifest), and removes the exemption (due 2026-12-31). Wiring `at risk design: placeholder brand` into the weekly report's At risk section changes SPEC-0016 and the facts schema, which the maintainers decide (due 2026-12-31).
- 2026-10-24: named colours are tested against a list of common names in colour properties only, and `url()` references to colours in SVG are not read; a mockup is reviewed by eye by its owner (due 2026-12-31).

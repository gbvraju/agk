# ADR-0248: the kit ships one design standard and check_design.py holds a theme to its theme and layout blocks (REQ-044, brief 455)

- Status: Proposed
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0204, SPEC-0037, SPEC-0029
- Requirements: REQ-044

Protected classes: `kit/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0037 (Approved; ADR-0204) gives a project's design phase one default UX standard that the kit ships, and a theme
that overrides only its brand roles, fonts and layout (rules 1 and 2). Today `/agk:design` writes a five-token block and
nothing else, so states, spacing and breakpoints are reinvented per page. Brief #455 is build (a) of rule 14, the first of
the seven design-phase builds (#455 to #461); the readings the conductor took where the spec is open are the field note of
2026-11-01 on #365. ADR-0204 decision 3 names the classes the builds change; this ADR names the ones this build changes,
because the protected-path check counts only an ADR of the same pull request (`Q-S0037-9`).

## Decision

1. **The tokens (answer 1).** `kit/templates/design-standard.css`, headed `/* agk design standard 1 */`, sets the sixteen
   colour roles `--color-<role>` (background, surface, text, muted, border, accent, on-accent, focus, and success,
   warning, danger and info, each with its `on-` role) in `:root` for light and again under
   `@media (prefers-color-scheme: dark)`; `--font-size-1` to `-6`, `--font-body` and `--font-heading` (system stacks);
   `--space-1` to `-8`; `--radius-1` to `-3`; `--elevation-1` to `-3`; `--motion-fast`, `-normal` and `-slow`, all `0ms`
   under `prefers-reduced-motion: reduce`; a `:focus-visible` outline in `--color-focus`; controls of at least 44 by 44 px;
   the `[data-density]` and `[data-align]` rules; and media queries at 360, 600, 900, 1200 and 1440 px. No colour is written
   outside the two token blocks, and the standard's own contrast pairs pass in both modes.
2. **The patterns (answer 2).** `kit/templates/design-patterns.md` has one `## <pattern>` section for each of the eleven
   patterns of rule 1, named in the spec's words, each with `### default` and the six required states, each one fenced
   `html` block of the standard's classes only (no `style`, colour, size or font), with fixture slots written `{{<key>}}`.
3. **The installed module (answer 3).** `scripts/agk/design_standard.py` (added to `verbatim` in `kit/manifest.json`, in
   sorted order) holds `STANDARD`, `ROLES`, `THEME_ROLES`, `FONT_TOKENS`, `DENSITY`, `ALIGNMENT`, `BREAKPOINTS`,
   `PATTERNS`, `REQUIRED_STATES`, `STATES`, `CONTRAST_PAIRS`, `OLD_TOKENS`, the standard's light and dark values,
   `theme_format(text)`, `standard_theme_problems(text)` and `theme_colours(text)`. It reads no file of the kit; the kit's
   tests prove its constants equal the two templates.
4. **The theme format (answer 4).** A theme on the standard has a line `Standard: agk design standard 1`; a `## Theme`
   section with one `css` block whose one `:root` rule, and at most one dark `:root` rule, set only the seven brand roles
   and the two font tokens; a `- logo:` line in the brand record, with its source as every brand value; and a `## Layout`
   section with `- density:` (`compact`, `comfortable` or `spacious`) and `- alignment:` (`start` or `centre`).
5. **The check (answer 5).** `check_design.py` reads the format with `theme_format`. On a standard theme it keeps the brand
   record and evidence checks and adds `standard_theme_problems` (`rule 2: docs/design/theme.md: the theme sets a token or
   rule outside its theme block`, `... the layout setting density (or alignment) is not one of the standard's`, never the
   value), and computes every pair of `CONTRAST_PAIRS` with its existing `contrast` on the standard's values after the
   overrides, light and dark (`rule 7: ... contrast below <4.5|3>:1 in <light|dark> for <role> on <role>`). The overrides
   follow the cascade of a `theme.css` loaded after the standard: a light value applies in dark too unless the dark rule
   sets the role.
6. **The old format (answer 6).** A theme without a `Standard:` line and its mockup folders are checked exactly as before;
   `tests/kit/test_check_design.py` is unchanged and green.
7. **The evidence line (answer 7).** The `EVIDENCE` pattern also accepts `docs/design/prototype/v<n>/`; such a folder that
   exists reads `design: the theme is not approved yet`, information, until #459 reads its sign-off row.
8. **Tests first (answer 8)** in `tests/kit/test_design_standard.py`; the docstring of `check_design.py` now says it is
   installed, as `kit/manifest.json` lists it.
9. **The spec (answer 9).** `docs/runs/proposed-spec-amendments-108.md` proposes the seven builds in rule 14. It is a
   proposal only; no rule in a spec changes.

## Consequences

Every later build of SPEC-0037 reads the names this one fixes. A project's existing theme and mockups keep passing; a
theme that gains the `Standard:` line is held to its two blocks, and its contrast is computed on what a page would show.
`kit/templates/design-theme.md` and `design.py` are unchanged until #457 moves a theme onto the standard.

## Residual

- 2026-11-01: Q-455-1 (the conductor's reading 1 on #365): the breakpoints are the five values listed (360, 600, 900,
  1200, 1440); "six" in `Q-S0037-1` is read as a slip until a person rules.
- 2026-11-01: Q-455-2 (reading 2): the brand roles are background, surface, text, muted, border, accent and on-accent;
  focus and the status roles are fixed by the standard, and a theme that sets one fails rule 2.
- 2026-11-01: Q-455-3 (reading 6): the eight builds of rule 14 become seven by amendment proposal 108, a proposal only.
- 2026-11-01: Q-455-4: a standard theme without a `- logo:` line in its brand record fails rule 2 (the brief names the line
  as part of the format; the conservative reading requires it).
- 2026-11-01: Q-455-5: the layout block must set both density and alignment, once each; a missing one fails as "not one of
  the standard's", and any other line of the layout block fails.
- 2026-11-01: Q-455-6: the contrast pairs are text, muted and accent on background and on surface, on-accent on accent and
  each `on-<status>` on its status at 4.5:1; border and focus on background and on surface at 3:1.
- 2026-11-01: Q-455-7: a colour role a theme sets must be a hex colour, as an old-format token in a contrast pair must, so
  the contrast can be computed; any other value fails rule 7 without the value.
- 2026-11-01: Q-455-8: any line starting `Standard:` makes the theme standard format; a number other than 1 fails rule 2,
  so a theme for a later standard is never checked as an old one.
- 2026-11-01: Q-455-9: the pattern sections are named in the spec's words (`## list with filter and sort`), and the
  standard's classes carry no prefix.

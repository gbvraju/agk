# ADR-0350: design_compare names match or drift of each built screen, and design.py screenshots writes reflow (REQ-044, brief 461)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0204, SPEC-0037, ADR-0252, ADR-0332
- Requirements: REQ-044

Protected classes: `scripts/agk/`, `skills/`, `.claude/`, `tests/kit_dev/`, `agk.toml`

## Context

SPEC-0037 rule 8 (build (e) of rule 14) says that `design.py screenshots --version <version>`
opens each page of a prototype version offline at each breakpoint, in light and dark, writes the
screenshots and records the reflow in `screenshots/reflow.json`; rule 11 (build (h)) says that the
builder of a UI build compares each named screen and state with the signed-off version and lists
match or drift, failing nothing, and that the conductor's verdict names every drift. Brief #461
folds the two builds into one (amendment 108 of #455), following the person's ruling 2 of
2026-10-30. ADR-0204 added REQ-044 and SPEC-0037 and says each build adds its own ADR citing it
(`Q-S0037-9`). This build writes its own ADR, not a `Covered-by:` line, for one reason: the
builder's standing rules add a `[[testing.map]]` entry to `agk.toml` for each new script, and
ADR-0204 decision 3 says no build changes `agk.toml` of this repository. That is the one decision
this ADR changes; no rule of the spec changes.

## Decision

1. **The renderer.** `scripts/agk/design_render.py` (new, kit-only, listed in the kit-only set of
   `tests/kit_dev/test_kit_manifest.py`, not in `kit/manifest.json`) reuses `design.py`'s
   `find_browser` and `SCHEME`. `measure(browser, page, width, mode)` opens the page inside an
   `iframe` of a wrapper page written to a temporary folder outside the version, with
   `--dump-dom`, `--allow-file-access-from-files` and `--host-resolver-rules=MAP * ~NOTFOUND`
   (measured on Chromium on 2026-11-08), and returns whether the document is wider than its
   viewport. `shoot(...)` writes one PNG with the same offline flags. `pixel_share(first, second)`
   decodes 8-bit, non-interlaced PNGs with `zlib` and returns the share of differing pixels, 1.0
   when the sizes differ; a file it cannot read is refused naming rule 11.
2. **`design.py screenshots --version v<n>`.** Beside the unchanged `--folder` of mockups (the two
   together are a usage error), it writes, for each `<screen>--<state>.html` of the version (not
   `index.html`, which is no screen), at each of `design_standard.BREAKPOINTS` and in light and
   dark, `screenshots/<screen>--<state>-<width>-<mode>.png` and one `screenshots/reflow.json`:
   `{"version": "v<n>", "entries": [{"page", "breakpoint", "mode", "result"}]}` with `result` one
   of `ok`, `sideways` or `not run`, the shape that `design_prototype_check.py` (#458) reads. Without a browser it prints
   `design: no headless browser found; reflow not run`, writes every entry as `not run` and exits 0.
   The docstring of `design.py` and `skills/design/SKILL.md` say that `screenshots/` is written only
   by `design.py screenshots`, never by hand.
3. **`scripts/agk/design_compare.py`** (new, kit-only, run by the builder session):
   `--version v<n> --screens "<screen>/<state>, ..." [--root DIR]`. A bare `*` is every page of
   the version; `<screen>/*` is every state of the screen, as `check_brief.py` reads a `Screens:`
   line (its `screens_named` is reused). It reads `[design]` through `common.config_source`, runs
   `render` (split by `shlex`, no shell, in the root) with `AGK_DESIGN_SCREEN`, `AGK_DESIGN_STATE`
   and `AGK_DESIGN_OUT` set to a temporary folder, reads `<out>/<screen>--<state>.html` and
   compares it with the frozen page:
   - structure: the landmarks (`header`, `nav`, `main`, `aside`, `footer`, `form`, `search` and a
     `role` of one), the heading outline (level and text), the controls with their labels (`input`,
     `select`, `textarea` and `button`, labelled by `aria-label`, a `label` for them or their own
     text) and the text of the links in order. The prototype's own parts are left out of the frozen
     page: the state bar (`id="states"`), the demo bar (`data-demo`), the link to `index.html` and
     the runtime's `script`. Link targets are not compared, since a built page's routes are not the
     prototype's file names.
   - tokens: the custom properties of the kit's standard (`kit/templates/design-standard.css`)
     referenced by `var()` in the page and in the stylesheets it links inside its own folder.
   - pixels, with a browser: `pixel_share` of a screenshot of each page at each breakpoint and
     mode, against `pixel_tolerance` (default 0.01, a number from 0 to 1).
4. **Its lines.** One line per screen and state: `<screen>/<state> match`, or
   `<screen>/<state> drift: <kinds>` with the kinds found, comma-separated, in the order
   structure, tokens, pixels; without a browser the line ends `; pixels: not run`. It exits 0 on
   drift. It exits 1, naming the setting or the rule and never a value, on a usage error, an unset
   `render`, a `pixel_tolerance` that is not a share, a version without a `design` row in
   `docs/design/signoffs.md`, a screen or state the version has no page for, and a `render` that
   exits non-zero or writes no page (nothing compared is never a match, `Q-461-2`).
5. **The conductor and the skill.** `skills/design/SKILL.md` gains the section that runs
   `design_compare.py` from the plugin root, so the command reaches a project (`parity.py`).
   `.claude/agents/conductor.md` gains: for every pull request of a UI brief,
   read its `Design match:` lines, ask for them by a fix list when they are missing, judge every
   drift, and the verdict names every screen and state that drifted with a fix item or a reason to
   accept it. Words are cut elsewhere in the file so that its rule budget does not grow.
   `check_pr_body.py` and `proof.py` do not change (`Q-S0037-11`).
6. **The guides.** `docs/guides/reference.md` describes `design.py screenshots --version`,
   `design_compare.py` and the `[design]` settings; `docs/guides/getting-started.md` adds the
   builder's step.
7. **`agk.toml`.** Two `[[testing.map]]` entries, one for each new script, so that the test plan
   selects their tests; the entry of `design.py` stays as it is on the default branch. This changes ADR-0204 decision 3 for these two entries only; no other line
   of `agk.toml` changes.

## Consequences

A UI build shows, before it is marked ready, where it departs from the signed-off version, and
the conductor judges each departure in its verdict; nothing fails automatically, as ruling 2 says.
A machine without a headless browser still gets the structure and token comparison, and its
reflow and pixel results read `not run`, never passed. A project without `render` gets a refusal
naming the setting when it runs the comparison, and nothing else changes for it.

## Residual

- 2026-11-08: the token comparison reads `var()` references in the page's own text and its linked
  stylesheets, not which rules of a stylesheet apply to the page, so a page that links the whole
  standard lists every token it references (due 2026-12-31).
- 2026-11-08: the pixel decode is pure Python; on a wide page a comparison takes seconds per
  screenshot.

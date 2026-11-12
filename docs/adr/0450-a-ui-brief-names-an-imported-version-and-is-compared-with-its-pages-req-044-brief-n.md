# ADR-0450: A UI brief names an imported version and is compared with its pages

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0037, ADR-0446, ADR-0448, ADR-0449, amendment 161, brief #1063, plan #661
- Requirements: REQ-044, REQ-036

## Context

Amendment 161 to SPEC-0037 (approved on #1057, ADR-0446) adds imported design versions `i<n>`. Build (a) (ADR-0448,
#1065) copies a customer's prototype into `docs/design/imported/i<n>/files/` with its manifest and map; build (b)
(ADR-0449, #1067) signs off and freezes the version. Item 5 says how a UI build is held to one. On the default branch
`check_brief.SCREENS` reads only `Screens: v<n> ...`, and `design_compare.py` compares a build with a kit version only.
This is build (c) of the amendment's item 8.

## Decision

1. `scripts/agk/check_brief.py` accepts `Screens: i<n> <screen>/<state>, ...`. The version needs a `design` row in
   `docs/design/signoffs.md` as before. Its pairs are the `<file> -> <screen>/<state>` rows of
   `docs/design/imported/i<n>/map.md`, read by `imported_map`: `*` is every state of the screen that the map covers,
   an `out:` row covers nothing, and with no map there is no covered pair. A pair the map does not cover is refused
   with `rule 10: a Screens screen or state is not covered by the map of the version`, and a version the sign-offs do
   not list with the existing `rule 10: the Screens version is not signed off in docs/design/signoffs.md`. Neither
   message names a value. `session.py`'s shared brief shape (`brief_problems`) does not read the `Screens:` line, so it
   needs no change.
2. `scripts/agk/design_compare.py --version i<n> --screens <line>` (kit-only) renders each screen with the project's
   `render` command and compares it with the file the map names. The structure and token comparisons do not apply.
   For a page (`.html`, `.htm`) it compares the visible text in order (the body's text without scripts, styles,
   templates and `hidden` elements) and, with a headless browser, the pixels at 1440 px in light mode within
   `pixel_tolerance`. For a picture page it compares pixels only. An image is compared at the width and height in its
   header (PNG, JPEG, WebP; 1440 by 800 px when the header gives none, as for an SVG). A PDF page
   `<file>#page=<n>` is rendered at 1440 px wide by `pdftoppm` where one is found.
3. Each line reads `<screen>/<state> match`, `<screen>/<state> drift: pixels, text` (the kinds found), the same with
   `; pixels: not run` when no browser is found, or `<screen>/<state> pixels: not run` for a picture page whose pixels
   could not be compared. The script never prints `match` for pixels it did not compare, and never prints `passed`.
   It exits 0 on drift. It exits 1, naming the rule or the setting, on a usage error, an unset or failing `render`, a
   version without a `design` row, or a pair the map does not cover.
4. The imported page is opened only by this script, through `FilesServer`. This is a server on 127.0.0.1 that the
   browser uses as its proxy for every request, the loopback included (`--proxy-server`,
   `--proxy-bypass-list=<-loopback>`, with the existing offline host rules; measured on a headless Google Chrome on
   2026-11-12: every request of a page, the browser's own included, reached the server). It serves `GET` and `HEAD` of
   `http://agk-imported.invalid/<path>` only for a file inside `docs/design/imported/i<n>/files/`, and answers 403 to
   every other request: another host, `https:` (`CONNECT`), a path outside the folder, a missing file, any other
   method. A page with an external reference therefore renders without it. No check and no workflow runs the script.

Protected path classes changed: `scripts/agk/` (`check_brief.py`, `design_compare.py`), `tests/kit/`
(`test_check_brief.py`) and `tests/kit_dev/` (`test_design_compare.py`). `kit/hashes.json` is changed only by
`kit_hashes.py`, if at all.

## Consequences

A UI build can be held to a customer's signed-off prototype the same way it is held to a kit version: by its brief's
`Screens:` line and by the builder's comparison before it marks the build ready. Only the visible text and, where a
browser runs, the pixels at one width are compared, so the kit standard's structure, tokens and other breakpoints are
still judged by the build's own checks.

## Residual

- 2026-11-12: `FilesServer` keeps the browser to the version's files by proxy, not by an operating-system sandbox. The
  imported page's scripts run in the headless browser (amendment 161 Residual) (due 2026-12-31).
- 2026-11-12: a PDF page is compared only where `pdftoppm` is installed; elsewhere it reads `pixels: not run`.
  Whether the kit should carry a renderer of its own is open (due 2026-12-31).
- 2026-11-12: the spec text of SPEC-0037 does not yet carry amendment 161; build (d) writes it (due 2026-11-30).

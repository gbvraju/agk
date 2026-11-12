# Proposed spec amendments 161 (SPEC-0037; REQ-044, REQ-036)

Date: 2026-11-11 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0446 (brief #1056), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0037-a-project-s-design-phase-delivers-a-click-through-prototype.md`. The number 161 is the one brief #1056
reserved. This amendment is not applied to the spec text in this pull request, which the brief limits to the amendment;
the four builds of item 8 write it into the text. The owner decides it with `Approve: <head> SPEC-0037` on this pull
request; no session posts it.

The sentence (brief #1056): "A project imports a customer's click-through prototype unchanged as a design version: every
file listed with its digest, every page mapped to the inventory, signed off, and UI builds compared with it."

The owner's direction, quoted as data (brief #1056, 2026-11-11 23:36 to 23:46 IST): "my org got a project from big
company, they have given click through prototype, we need to convert that into brief and specs, deliver it with AGK.
Without loosing anything"; "lets say we have #6 prototype from the customer"; "How about KIT change"; "File it".

## What is on the default branch today

Read in the code by this session:

- Rule 4: `/agk:design prototype` (`scripts/agk/design.py prototype`, `scripts/agk/design_prototype.py`) writes
  `docs/design/prototype/v<n>/` from the standard, the theme, the approved inventory and the fixture set, and from
  nothing else.
- Rules 5 to 7: `scripts/agk/design_prototype_check.py`, called by `check_design.py`, fails an inline script, an event
  handler, a script other than the hashed runtime, a stylesheet other than the folder's `standard.css` and `theme.css`,
  a colour outside the tokens and data outside the fixture set. A customer's prototype fails these by design.
- Rule 9: `scripts/agk/reviewers.py` `APPROVE_DESIGN` matches only `Approve: design v<n> <40-hex>`;
  `scripts/agk/design_signoff.py` (`VERSION = ^v[1-9]\d*$`, `version_digest`) freezes a version by its digest.
- Rules 10 and 11: `scripts/agk/check_brief.py` `SCREENS` reads only `Screens: v<n> ...`; `scripts/agk/design_compare.py`
  compares a build with a kit version by structure, tokens and pixels.
- Rule 13: no real data, name or text from `private/` or `reference/` in a theme, an inventory, a fixture or a
  prototype. Nothing checks that every screen of a customer's prototype reached the inventory.

## Items

1. **A new rule 15, the imported version.** "`/agk:design import <folder>` (`scripts/agk/design.py import`) makes an
   imported version `i<n>`, the next free number (`i1`, `i2`, ...), never overwriting one (`Q-S0037-12`). It copies every
   file of the folder byte for byte into `docs/design/imported/i<n>/files/`, keeping each relative path (`Q-S0037-18`),
   and writes beside that folder `docs/design/imported/i<n>/manifest.json`: one entry per file with its relative path,
   its size in bytes and its SHA-256, sorted by path, and `digest`, the SHA-256 of the sorted list of
   `<path> <SHA-256 of the file>` lines, the formula of rule 9. Nothing is edited, renamed, minified, converted or left
   out; every file is copied, whatever its type (`Q-S0037-17`). The command refuses, naming the rule and the file and
   copying nothing, a symbolic link, a source folder inside `docs/design/`, and an empty folder. It reads files only:
   no network, no model, and it opens no page. Of the copied files:
   - an HTML file (`.html`, `.htm`) is a **page**;
   - an image (PNG, JPEG, SVG, WebP) that no page of the version references by a relative link, `src` or CSS `url()` is
     a **picture page**; one that a page references is an asset of that page and needs no row;
   - each page of a PDF is a picture page, named `<file>#page=<n>` (`Q-S0037-13`);
   - every other file (a stylesheet, a script, a font, data) is an asset and needs no row.
   Pages and picture pages are listed in the manifest's `pages` list, which the import computes from the files alone."
2. **Rule 15, the screen map: nothing lost.** "`docs/design/imported/i<n>/map.md` holds one row per page and picture page
   of the manifest, either `<file> -> <screen>/<state>`, with a screen and state of `docs/design/inventory.md`, or
   `<file> -> out: <reason>`. The map is the person's work; the session may draft it, and the check only judges it.
   `check_design.py` fails, naming the rule and the file (or the screen and state), never a value:
   - a page or picture page of the manifest with no row;
   - a row naming no page or picture page of the manifest, or a file twice;
   - a row naming a screen or a state that is not in the inventory, or a state the inventory marks `n/a:`;
   - two rows of one version naming the same screen and state (`Q-S0037-16`);
   - an `out:` row with no reason;
   - a screen and state that the inventory marks `yes` and that neither a row of an imported version nor a page of a kit
     version covers.
   The coverage reads every version folder on the branch, `v<n>` and `i<n>` alike, signed off or not; rule 7's check for
   a missing page still applies to each kit version on its own. The inventory is still made by rule 3 from the
   requirements and the specs alone; an imported prototype informs the requirements through the person, and its text
   is never copied into the inventory (`Q-S0037-19`)."
3. **Rule 15, the import checks, and rule 13.** "`check_design.py`, with a new installed module
   `scripts/agk/design_import.py` that it imports, checks each imported version folder: a file of `files/` that the
   manifest does not list, a listed file that is missing, a size or SHA-256 that does not match, a `digest` or a `pages`
   list that does not follow from the files, and the map rules of item 2, each failing naming the rule and the file.
   Rules 5, 6 and 7 do not apply to an imported version. Its pages are never run by a check, a command or a workflow:
   every check reads them as text only. Every external reference a page or a stylesheet makes (a URL that starts
   `http:`, `https:` or `//`) is listed, one per line with its file, in `docs/design/imported/i<n>/external.txt`, which
   the import writes and the check recomputes and compares; the list informs the person and blocks nothing
   (`Q-S0037-14`). Rule 13 changes so: its first sentence holds everywhere outside `docs/design/imported/`, and nothing of
   an imported version (no text, no value, no file) is copied into a theme, the inventory, a fixture, a test or a kit
   prototype version. What may be committed to the project's repository is the person's call before the import; the
   secret scan runs over the copy as over any tracked file, and no ignore entry is added for it (principle 9)."
4. **Rule 9, the sign-off of an imported version.** "A person signs off an imported version with
   `Approve: design i<n> <full head ID>` by an account in `spec_approvers`, on the head it names, as for a kit version,
   inside a solo-mode `Confirmed:` comment too; a session never posts it. The session appends one `design` row to
   `docs/design/signoffs.md` with the version `i<n>` and the digest of the whole folder `docs/design/imported/i<n>/`
   (`files/`, `manifest.json`, `map.md` and `external.txt`, by the formula of rule 9), and `check_final_clearance.py`
   counts the row only with that line. Once signed off the folder is frozen: a change, an addition or a removal fails
   naming the rule and the version; a corrected map or a new delivery from the customer is a new version `i<n+1>`,
   imported again, never an edit in place." `APPROVE_DESIGN` and `design_signoff.VERSION` accept `i<n>` beside `v<n>`.
5. **Rules 10 and 11, builds held to an imported version.** "A UI brief's `Screens:` line may name `i<n>` with screens and
   states that its map covers (`*` is every state of the screen that the map covers); `check_brief.py` refuses a screen
   or state the map does not cover, and a version that `docs/design/signoffs.md` does not list. Before marking ready,
   the builder runs `design_compare.py --version i<n> --screens <the line>`. For a page it renders the built screen and
   the imported page, both offline, and compares the pixels within `pixel_tolerance` (`Q-S0037-15`) at 1440 px in light
   mode, and the page's visible text, in order; for a picture page it compares the pixels only, at the width of the
   image (for a PDF page, the page rendered at 1440 px wide). The structure and token comparisons of rule 11 do not
   apply. Each line reads `match`, `drift: pixels|text`, or `pixels: not run` without a headless browser, never passed
   (rule 8); the exit is 0 on drift, as today. The imported page is opened only by this kit-only script, which the
   builder runs: with every request outside `docs/design/imported/i<n>/files/` refused, so a page with an external
   reference renders without it, and never by a check or a workflow."
6. **Both kinds in one project.** "A project may hold kit versions `v<n>` and imported versions `i<n>`; item 2's coverage
   reads both. `docs/guides/product-owner.md` and `/agk:design` (`skills/design/SKILL.md`) say when to import (the
   customer's prototype is the design) and when to draw (no prototype yet), and `doctor.py` reports each imported
   version's manifest and map state as information."
7. **Tests (for the builds).** Fixture prototypes of invented pages only, `example.com` links, in `tmp_path`, no network:
   - the import of a fixture folder copies every file byte for byte, `i1` then `i2`, never over an existing one; the
     manifest lists each path, size and SHA-256, and its digest is stable and changes with one byte; a symbolic link,
     a source inside `docs/design/` and an empty folder are refused naming the rule and copy nothing;
   - pages, picture pages (an unreferenced image, each page of a PDF) and assets (a referenced image, a stylesheet, a
     script) are classified as item 1 says;
   - a missing, added or changed file fails naming the file; a page with no row, a row for no file, a file twice, an
     unknown screen or state, an `n/a:` state, a screen and state twice, an `out:` row with no reason, and a `yes` state
     that no version covers each fail naming the rule; a complete map passes, and a `yes` state covered only by a kit
     page passes;
   - an imported page with an inline script, an external stylesheet and a colour outside the tokens passes rules 5 to 7,
     because they do not apply, and its external reference appears in `external.txt`; no test opens a page;
   - `Approve: design i1 <head>` by a listed account counts, by another account or on another head does not; a signed-off
     imported folder with a changed map fails naming the version;
   - `Screens: i1 <screen>/<state>` passes for a mapped state and is refused for an unmapped one; the comparison prints
     `pixels: not run` without a browser and never `match` for pixels it did not compare;
   - the texts of the guide and the skill say when to import and when to draw.
8. **The builds that follow (rule 14).** Tests first, each from the default branch with its own ADR naming the protected
   classes it changes and one fragment under `changelog.d/`, each 600 changed lines or fewer, after this amendment's
   `Approve: <head> SPEC-0037`:
   - (a) the import, the manifest and the map check (items 1 to 3): `scripts/agk/design.py`, `scripts/agk/design_import.py`
     (new, installed, added to `verbatim` in `kit/manifest.json`), `scripts/agk/check_design.py`,
     `tests/kit/test_design_import.py`;
   - (b) the sign-off (item 4): `scripts/agk/reviewers.py`, `scripts/agk/design_signoff.py`,
     `scripts/agk/check_final_clearance.py`, `tests/kit/test_design_signoff.py`; in parallel with (a);
   - (c) `Screens:` and the comparison (item 5): `scripts/agk/check_brief.py`, `scripts/agk/session.py` (the shared brief
     shape), `scripts/agk/design_compare.py`, `tests/kit_dev/test_design_compare.py`; `Depends-on` (a);
   - (d) the guides and doctor (item 6): `docs/guides/product-owner.md`, `docs/guides/getting-started.md`,
     `skills/design/SKILL.md`, `scripts/agk/doctor.py`, `tests/kit/test_doctor.py`; in parallel with (c).
9. **Not in this amendment.** Rules 1 to 8 and 12 are unchanged for kit versions; a kit version is still written only by
   `/agk:design prototype`, and mockup folders are read as before. No workflow changes, and no workflow installs a
   browser. No session approves an imported version.

## Contexts

- kit: the import, the checks and the sign-off are installed, so every customer project can import its prototype.
- github: no workflow change; imported pages are never run in CI, only read as text by `check_design.py`.
- local: the same commands on a laptop; the comparison needs a headless browser where it runs, else `pixels: not run`.
- personal: the same as local.
- stacks: not applicable; no test or build step of a stack changes.

## Residual

- 2026-11-11: an imported prototype may hold the customer's real names and data; no check can tell them from invented
  ones, so what is committed is the person's call before the import (due 2026-12-31).
- 2026-11-11: imported pages are not held to the standard's tokens, accessibility or fixture data; a build that matches
  one inherits what it lacks, and only the person's review catches it (due 2026-12-31).
- 2026-11-11: the comparison runs the imported page's scripts in a headless browser; it is held offline and to the
  version folder by the script, not by a sandbox of the operating system (due 2026-12-31).
- 2026-11-11: pixels at one width and in light mode only say nothing of the build's other breakpoints, which the kit
  standard and rule 7's checks on the build's own code still cover (due 2026-12-31).

## Questions

Each reading is the most conservative one, and applies until a person rules.

- Q-S0037-12: the version prefix. Reading: `i<n>`, numbered apart from `v<n>`, so a kit version and an imported version
  are never confused in a `Screens:` line or a sign-off row.
- Q-S0037-13: does a PDF or an exported design frame count as pages? Reading: one picture page per PDF page
  (`<file>#page=<n>`) and one per exported frame image; a design tool's own project file is an asset, kept but not mapped.
- Q-S0037-14: does a non-empty `external.txt` block sign-off? Reading: no, it informs the person; the comparison renders
  without those references.
- Q-S0037-15: the pixel tolerance for imported pages. Reading: the project's `pixel_tolerance` of the `[design]` table,
  as for kit versions; no setting of its own.
- Q-S0037-16: may two files map to one screen and state in one version? Reading: no; the comparison needs one reference,
  and a second file maps to the same screen's other state or `out:` with its reason.
- Q-S0037-17: the brief keeps "HTML, CSS, images and PDF". Reading: every file is copied and listed whatever its type,
  because leaving one out would lose it; only pages and picture pages need a map row.
- Q-S0037-18: the brief copies into `i<n>/` with `manifest.json` "beside it". Reading: the files go into `i<n>/files/`, so
  a customer's own file named `manifest.json`, `map.md` or `external.txt` never collides with the kit's records.
- Q-S0037-19: may the inventory be drafted from the imported prototype? Reading: no; rule 3 fills it from the requirements
  and the specs only, and rule 13 keeps the prototype's text out of it; the person turns the prototype into requirements,
  and the map then proves each screen reached the inventory.

# ADR-0458: An imported prototype becomes a plan source, one heading per mapped screen and state

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0037, ADR-0269, ADR-0446, ADR-0448, ADR-0454, ADR-0455, amendment 161, amendment 163,
  brief #1077, brief #1073, plan #661
- Requirements: REQ-050, REQ-044

## Context

Amendment 163 item 2 (ADR-0454) adds SPEC-0043 rule 2a: an imported prototype `docs/design/imported/i<n>/` (SPEC-0037
rule 15 as amendment 161 proposes, ADR-0448) becomes a `Kind: design` source with one `## <screen>/<state>` heading per
mapped row and the page's visible text under it. On the default branch at 3e38560 nothing writes that file: build (b)
(ADR-0455, `check_plan.py`) checks a source's header and resolves its locations, and `design_import.py` imports and
checks a version, but no command turns a mapped version into a source. This is build (k). The owner ruled `Q-1073-2` on
#1080 (comment 6815621344) after the amendment's text was written and before it merged: "read every visible text of a
page (all text outside script, style and template elements, in document order), not only role alert or status, so no
message of the prototype is lost."

## Decision

1. `python3 scripts/agk/design_import.py source --version i<n> --slug <slug> [--root DIR]` (installed: the module is
   already in `verbatim` of `kit/manifest.json`) writes once, as a new file only, `docs/sources/<slug>-prototype-i<n>.md`:
   `Source: imported prototype i<n>`, `Kind: design`, `Version: i<n> <the manifest's digest>`, `Date:` from the clock in
   UTC, one blank line; then for each row of the version's `map.md` that is not `out:`, in the map's order, one
   `## <screen>/<state>` heading and under it the page's visible text, or `picture: <file>` for a picture page.
2. The visible text follows the ruling on `Q-1073-2`: every text of the page outside `script`, `style` and `template`
   elements, in document order, read with the standard library's HTML parser as text (comments are not text), with the
   `name` and `placeholder` of each `input`, `select` and `textarea` and the `value` of an input button, one per line,
   white space collapsed, empty ones left out. Text inside phrasing elements (`b`, `em`, `span` and the like) runs on
   with its line; every other tag ends a line. A line that starts `#`, ```` ``` ```` or `~~~` gets a leading backslash,
   so a text of the page is never read as a heading or a fence of the source.
3. It refuses with exit 1, naming the rule (`rule 2a`) and the version and writing nothing, a version that is not in
   `docs/design/imported/` and a version for which `imported_problems` reports a problem of that version's folder or of
   the coverage; it refuses an existing target file, naming the file; a missing or malformed `--slug`
   (`[a-z0-9][a-z0-9-]*`, `Q-1073-1`) or `--version` exits 2 naming the option. `source_text(root, version)` returns the
   text and writes nothing. No page is run or opened, no network, no model.

Protected path classes changed: `scripts/agk/` (`design_import.py`) and `tests/kit/` (`test_design_import_source.py`).
`kit_hashes.py` prints `ok kit-hashes` and leaves `kit/hashes.json` unchanged.

## Consequences

A person with an imported, mapped prototype gets, in one command, a source whose every heading is a location that
`check_plan.location_problem` resolves (`<file>#<screen>/<state>`), so build (d) can count it and build (c) can draft
from it. The text of every message, hint and label of a page is kept, as the ruling asks, so the person has more to
clean than the amendment's narrower list would have given.

## Residual

- 2026-11-12: the subcommand lives in `design_import.py`, as brief #1077 says; amendment 163 item 2 names
  `design.py source`, which is kit-only and not in the brief's `Touches:`, so no `design.py` subcommand exists
  (`Q-1077-1`) (due 2026-11-30).
- 2026-11-12: amendment 163 item 2's text still lists `role="alert"` or `role="status"` only; the ruling on `Q-1073-2`
  stands over it until the spec text is written (due 2026-12-31).
- 2026-11-12: text drawn by CSS (`content:`) or by a script, and an image's `alt`, are not read (due 2026-12-31).

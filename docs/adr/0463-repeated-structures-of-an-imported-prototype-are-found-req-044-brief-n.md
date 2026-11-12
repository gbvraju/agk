# ADR-0463: The structures an imported prototype repeats across its pages are found and written as a design source

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0037, SPEC-0043, ADR-0269, ADR-0448, ADR-0454, ADR-0458, ADR-0469, amendment 161, amendment 163,
  amendment 164, brief #1091, brief #1089, brief #1077, plan #661
- Requirements: REQ-044, REQ-050

## Context

Amendment 164 item 3 (ADR-0469, approved by the owner's `Approve:` lines for SPEC-0043 and SPEC-0037 on #1097) adds
SPEC-0037 rule 16: `design_import.py components` finds the element structures that two or more mapped pages of an
imported version share and writes them as a `Kind: design` source, so that build (r) can propose shared components for
a `Foundation` milestone. On the default branch at 42479be `design_import.py` imports a version, checks it and writes its
prototype source (`source`, ADR-0458), but finds nothing that repeats across pages. This is build (q).

## Decision

1. `python3 scripts/agk/design_import.py components --version i<n> --slug <slug> [--root DIR]` (installed: the module
   is already in `verbatim` of `kit/manifest.json`) writes once, as a new file only, `docs/sources/<slug>-components-i<n>.md`:
   `Source: shared components of imported prototype i<n>`, `Kind: design`, `Version: i<n> <the manifest's digest>`,
   `Date:` from the clock in UTC, one blank line.
2. A mapped page is the file of a row of `map.md` that is not `out:` and is an HTML page, not a picture page. The page is
   read with the standard library's HTML parser as text. The elements read are those below `body`, never `html`, `head`,
   `body` or what `head` holds. The structure of an element is its tag, its class names in the order written and its
   child elements' tags in order; its text, its other attributes and its children's own structure are left out.
3. A structure is listed when it appears on two or more different mapped pages, the element has a child element or a
   class name, and it is not inside a listed structure that appears on exactly the same pages, the reading of
   `Q-1089-5`: inside means that every occurrence of it has an occurrence of that structure among its ancestors.
4. Each listed structure is one `## <name>` heading in the order of its first appearance (the map's order, then document
   order). The name is its first class name, else its tag path from `body` joined with `>` (also when the first class
   name holds `/`), with `-2`, `-3`, ... added to a name already used. Under it, after one blank line: one line
   `structure: <tag>.<class>...: <child tags>` (child tags separated by one space, nothing after the colon for an element
   without children), then one line `- <screen>/<state>` per mapped row it appears on, in the map's order. With nothing
   listed the file holds the header and the one line `none: no element structure appears on two or more mapped pages`.
5. It refuses with exit 1, naming `rule 16` and the version and writing nothing, a version that is not on the branch and
   one for which `imported_problems` reports a problem of that version or of the coverage; it refuses an existing target
   file, naming the file; a missing or malformed `--slug` or `--version` exits 2 naming the option. `components_text`
   returns the text and writes nothing. No page is run or opened, no network, no model.

Protected path classes changed: `scripts/agk/` (`design_import.py`) and `tests/kit/` (`test_design_import_components.py`).
`kit_hashes.py` prints `ok kit-hashes` and leaves `kit/hashes.json` unchanged.

## Consequences

A person with an imported, mapped prototype gets in one command the list of what its pages share, with the screens that
use each one; the list carries tag, class, screen and state names only, never a page's text. Build (r) reads it to
propose components, and the person edits the proposals before `render`.

## Residual

- 2026-11-12: brief #1091 answer 1 says sorted class names, outermost nesting only and output sorted by name; amendment
  164 item 3, which the owner's fire message says to follow, says class names as written, `Q-1089-5`'s nesting and
  first-appearance order, and this build follows the amendment (`Q-1091-1`) (due 2026-11-30).
- 2026-11-12: the texts of SPEC-0037 rules 13 and 16 are not written into the spec here; the brief's `Touches:` does not
  name the spec, and amendment 161 was written into SPEC-0037 by its own brief (#1064) (`Q-1091-2`) (due 2026-12-31).
- 2026-11-12: structure only: the same component written with other markup is not matched, and a plain repeated list
  may be listed (amendment 164's residual) (due 2026-12-31).

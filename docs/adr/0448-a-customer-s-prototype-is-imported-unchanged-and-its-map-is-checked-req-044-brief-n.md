# ADR-0448: A customer's prototype is imported unchanged and its map is checked

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: brief #1061, SPEC-0037, amendment 161 (`docs/runs/proposed-spec-amendments-161.md`, #1057), ADR-0446, Q-1061-1, Q-1061-2, Q-1061-3
- Requirements: REQ-044, REQ-036

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

Amendment 161 to SPEC-0037, approved on #1057 (`Approve: c9bae51f452165b8f15283c470885e2d9a6f98bd SPEC-0037`),
adds rule 15, the imported version, and lists four builds in its item 8. This is build (a), items 1 to 3: the import,
the manifest and the map check. Before it, `design.py` had no `import` command and `check_design.py` read nothing under
`docs/design/imported/`.

## Decision

1. `python3 scripts/agk/design.py import <folder>` makes the next imported version `i<n>`, never over an existing one,
   and copies every file of the folder byte for byte into `docs/design/imported/i<n>/files/`, keeping each relative
   path. Beside it, it writes `manifest.json` (one entry per file with `path`, `size` and `sha256`, sorted by path;
   `digest`, the SHA-256 of the sorted `<path> <SHA-256 of the file>` lines, paths relative to `files/`; and `pages`)
   and `external.txt` (one `<file> <url>` line per reference to `http:`, `https:` or `//` in a page or a stylesheet).
   It refuses, naming the rule and the file and copying nothing, a symbolic link, a source folder inside
   `docs/design/` and a folder with no file.
2. An HTML file is a page; an image (PNG, JPEG, SVG, WebP) that no page references by a relative `href`, `src`,
   `srcset`, `poster`, `data` or CSS `url()` is a picture page; each page of a PDF is a picture page
   `<file>#page=<n>`, counted from the PDF's bytes; every other file is an asset.
3. The new installed module `scripts/agk/design_import.py` (in `verbatim` of `kit/manifest.json`), imported by
   `check_design.py`, checks each imported version: a file of `files/` the manifest does not list, a listed file
   that is missing, a size or SHA-256 that does not match, a `digest`, `pages` list or `external.txt` that does not
   follow from the files, and the rules of `map.md` of amendment item 2. With at least one imported version and an
   inventory, every `yes` state of the inventory must be covered by a row of an imported version or a page
   `<screen>--<state>.html` of a kit version `v<n>`. Rules 5, 6 and 7 do not apply to an imported version. Every file
   is read as bytes or text; no page is opened or run, no network, no model, and the check writes nothing.
4. `agk.toml` gains one `[[testing.map]]` entry for `scripts/agk/design_import.py`, and
   `tests/kit/test_design_import.py` joins the `tests` of the `scripts/agk/check_design.py` and `scripts/agk/design.py`
   entries (the answer to Q-1061-3 on #1065); no other line changes.
5. The spec text is not changed here; build (d) writes the amendment into it. Items 4 to 6 are builds (b) to (d).

## Consequences

A project can hold a customer's prototype as it was delivered, and `check_design.py` fails a changed, added or
missing file and any page or picture page the map loses. A project with no imported version reads exactly as before.
The import copies whatever the folder holds; what may be committed stays the person's call before the import, and the
secret scan reads the copy as any tracked file.

## Residual

- 2026-11-12: the coverage of `yes` states applies only once an imported version exists, so a project with only kit
  versions is held by rule 7 alone, as before (Q-1061-1; due 2026-12-31).
- 2026-11-12: the PDF page count reads the file's bytes without a PDF reader; a PDF whose page objects are all inside
  compressed object streams counts by its `/Count`, else as one page (Q-1061-2; due 2026-12-31).

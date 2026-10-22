# ADR-0070: the report is built as a structure and rendered from it (REQ-029 part R1, SPEC-0022), kit 0.37.0

- Status: Accepted
- Date: 2026-10-22
- Deciders: maintainers
- Related: ADR-0069, ADR-0063
- Requirements: REQ-029

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

SPEC-0022 (Approved, #120) makes the weekly report available as data, in a `report.json` next to `facts.json`, so that any reader can show the same report without reimplementing its rules. Evidence:
reproducing the report's rules in another program was measured at about 2,300 changed lines; data removes that duplication and the drift it invites. The build is large (about 1,100 lines of code and tests), so
the maintainers split it in three: this part R1 builds the structure and the renderer for the opening, Delivered, Proven, Cost and the notices; R2 builds Needs you, the inbox and At risk; R3 writes the document,
the schema and the artifact with its second file. In every part the markdown and the inbox goldens are byte-identical to before. The tests were written first and run on unchanged `main` (49 failed; the output is
in the pull request body).

## Decision

1. **The structure** (SPEC-0022 rules 2 to 5): `product_report.build_report(doc, today, week)` returns `{"schema", "week", "opening", "sections", "notices"}`. The sections Delivered, Proven and Cost, and the
   notices (the footer: facts commit, kit version, a modified tree, the metrics issue, the drift-audit issue) are lists of items `{"kind", <fields>, "links"}`. The kinds and their fields are the table
   `ITEM_KINDS` (with `OPTIONAL_FIELDS` for the issue number and title, present when found), as in SPEC-0022 rule 5; a link is `{"to", "url"}`. Unknown values are the string `unknown`; no value is null or a float.
2. **The renderer** (`render_markdown(structure)`): a function of the structure and nothing else, so the markdown is rendered from the same data a reader would get; `render_report(doc, today, week)` is
   `render_markdown(build_report(...))`. The text of every line is unchanged: the existing report goldens, the inbox goldens and every other report test pass without a change.
3. **Transitional:** Needs you and At risk are lists of items of the kind `line` (`{"kind": "line", "text"}`), one per printed line, until part R2 replaces them. The kind is not in `ITEM_KINDS` and is
   never published (no file is written in this part).
4. **The inbox** keeps its own builders and `footer_head` in this part; R2 builds it from the same item builders.
5. **Amendment 34** (`docs/runs/proposed-spec-amendments-34.md`) is applied to SPEC-0011 rule 8 (the structure, the transitional kind) and rule 13 (the new test).
6. **Tests, first** (`tests/kit/test_report_structure.py`, new): the markdown rendered from the structure, also after a trip through JSON, equals what the script prints for every golden facts; the renderer
   takes the structure and nothing else; the document keys, the fixed kinds, exactly the fields of a kind, the link targets; no value is null or a float; the unknown items; every kind of the table is built by some
   golden; Needs you and At risk are `line` items and the covered sections have none.
7. **Kit 0.37.0**: the manifest `kit_version`, the hash of `scripts/agk/product_report.py`, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). No file is added to or removed
   from the manifest.

## Consequences

- Nothing the report prints changes; a project's next report is byte-identical for the same facts.
- `product_report.py` grows by the structure and a renderer table; the imports and the single file read are unchanged (SPEC-0011 rule 13).
- R2 and R3 follow, with kits 0.38.0 and 0.39.0; REQ-029 stays `planned` until R3.

## Residual

- 2026-10-22: the kind `line` exists until part R2 (due 2026-11-15).

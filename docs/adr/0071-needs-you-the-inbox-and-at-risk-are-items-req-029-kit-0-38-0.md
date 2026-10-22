# ADR-0071: Needs you, the inbox and At risk are built as items (REQ-029 part R2, SPEC-0022), kit 0.38.0

- Status: Proposed
- Date: 2026-10-22
- Deciders: maintainers
- Related: ADR-0070, ADR-0069
- Requirements: REQ-029

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

Part R1 (ADR-0070) built the opening, Delivered, Proven, Cost and the notices as items and rendered the markdown from them, leaving Needs you and At risk as lines of text (the transitional kind `line`).
This part R2 builds those two the same way and builds the inbox from the same item builders, so every section of the report is data (SPEC-0022 rules 2 to 5). The markdown and the inbox goldens stay
byte-identical. The tests were written first and run on unchanged `main` (51 failed, 43 passed; the output is in the pull request body).

## Decision

1. **Needs you and the inbox:** `inbox(doc, links, today)` returns the groups `{"group", "count", "items"}` (`count` is `unknown` when the first item of the group is an `unknown` item). The six builders return items
   of the kinds `draft-spec`, `proposed-adr`, `question`, `pull-request-no-verdict`, `overdue-residual`, `unspecced-requirement` and `unknown`. `build_report` puts the groups in `needs_you`; `render_inbox` prints
   the same groups with the footer of the facts commit and a modified tree (the notices `facts-commit` and `working-tree-modified`), so `footer_head` is removed.
2. **At risk:** `at_risk` returns items of the kinds `residual-overdue`, `pull-requests-open-long`, `pull-requests-sent-back`, `pull-requests-merged-no-verdict`, `pull-requests-merged-not-cleared`,
   `drift-audit` and `unknown`. `by_kind` becomes `grouped`: a kind with two or more pull requests is one item at the place of its lowest number, with one link per entry; a kind with one keeps one entry and,
   for the two kinds that print it, its title. `cleared_line` becomes `cleared_state` (`no-verdict`, `not-cleared` or none); `drift_line` becomes `drift_item` (`total`, `counts`, `open_issue`).
3. **The transitional kind `line` is removed** from the structure, the renderer and the table; `ITEM_KINDS` and `RENDER` hold the same 26 kinds, and the structure has no free text.
4. **Renderers:** one function per kind in `RENDER`; the grouped lines render the entries with the links the item carries.
5. **Amendment 35** (`docs/runs/proposed-spec-amendments-35.md`): SPEC-0011 rule 8; SPEC-0022 rule 3 (the group names), rule 5 (titles only where the report prints them; the `what` value of the age-limit line).
6. **Tests, first** (`tests/kit/test_report_structure.py`, extended): every section and Needs you's groups are items of the fixed kinds; the kind table is the 26 kinds and `line` is gone; the groups have a count
   (`unknown` for an unknown item); titles only where printed; the inbox prints the same groups as Needs you; the markdown from the structure, also after a trip through JSON, equals the printed report.
7. **Kit 0.38.0**: the manifest `kit_version`, the hash of `scripts/agk/product_report.py`, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). No file is added to or removed
   from the manifest.

## Consequences

- Nothing the report or the inbox prints changes; for the same facts both are byte-identical to before.
- Every section of the report is data now; R3 writes it as `report.json` with its schema and the second file of the artifact.

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-223 | The `unknown` item of the drift counts links to the repository's list of issues; which link target? | `search`, as the list of pull requests (Q-K4-222, ruled as read): a listing, not a path. Proposed for ruling. |

## Residual

None.

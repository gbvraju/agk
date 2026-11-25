# ADR-0812: One product glossary from a kit template, its form check in the gates and checklist item 1

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0073, SPEC-0074, ADR-0801, ADR-0668, ADR-0675, ADR-0793, brief #1951, brief #1933, plan #661
- Requirements: REQ-080

Protected classes: `scripts/agk/`, `config/`, `kit/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0073 (Approved) rule 8, "Language: one product glossary" (`Q-S0073-5`), and rule 15 build (e). Before this
change, on the default branch at 1fb8181c, no file of `scripts/agk/` or `kit/templates/` held a glossary, and
`[quality] glossary_terms` (ADR-0801) had no reader: a `docs/glossary.md` with 41 rows and a term twice passed every
step. `config/review-checklist.md` changes only by a decision record that cites a row of a catch log (its header).

## Decision

1. `kit/templates/glossary.md` is a short header (what the file is, that it holds only the project's own terms, that the
   steward's `Term:` notes stay) and one empty table `| Term | Meaning | In code | Synonyms |`. It is read from the
   kit root, as `layers.py` reads `kit/templates/architecture.md`, and is not a `templates` entry of
   `kit/manifest.json`, so no install writes a glossary and every project today is unchanged.
2. `scripts/agk/gates/glossary.py --write` writes `docs/glossary.md` from the template once and refuses an existing
   file, `the glossary exists (path class: docs/glossary.md)` (`Q-73E-1`). Seeding it from the grill and the memory's
   `Term:` entries is the steward's, by hand, in planning; no reader of the memory issue is added (`Q-73E-2`).
3. `glossary.py` is a step of the runner's interface (`RULE`, `check`, `applies`), installed (one `verbatim` row of
   `kit/manifest.json`) and run by `run_gates.py` as the new tuple `QUALITY_STEPS = ("glossary",)` after
   `PRODUCT_STEPS`, only where `docs/glossary.md` exists. It fails: no table, two tables or other columns; a row with
   other cells, or an empty `Term` or `Meaning`; a term twice, compared case-folded and trimmed against every term and
   synonym of an earlier row; more data rows than `[quality] glossary_terms`. Several names in `In code` are one row.
   Each failure names `SPEC-0073 rule 8`, the path class `docs/glossary.md` and the row number, never a term
   (principle 8). A cap outside 10 to 200, a `bool` or a string fails with `config.quality_settings`'s own line,
   `the [quality] table is refused (setting: quality.glossary_terms)`; the other `[quality]` keys are not read. Files
   only, no network; the same in `prepush.py`, `make governance` and the `proof` job.
4. Review checklist item 1 (`wrong-assumption`) becomes "which assumption, or term (against docs/glossary.md), did you
   check against the record, and what did it say?": 18 words, as before, so `config/rule-budget.txt` is unchanged. It
   cites the catch log row `docs/runs/architect-catches-1.md` row 18 (kind `wrong-assumption`: a word of the charter,
   the repositories, read one way while the customers meant another), the row the brief's `Q-73E-3` reading asks for.
   It stays one question of item 1, never a judgement gate.

## Consequences

A project's words have one checked home and the reviewer asks for a term against it; SPEC-0074 build (d) adds the
packs' line and their synonyms to this one glossary. With no `docs/glossary.md` nothing runs and nothing prints. No
workflow, label, required check, `agk.mk` recipe or governance step list changes; `kit/hashes.json` and the version stay
the release's.

## Residual

- 2026-11-25: the packs' synonyms by reference, outside the cap (SPEC-0074 rule 7), are SPEC-0074 build (d)'s.

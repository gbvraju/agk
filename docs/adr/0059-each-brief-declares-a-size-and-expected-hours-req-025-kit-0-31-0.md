# ADR-0059: each brief declares a size and expected hours, compared with the actual (REQ-025, SPEC-0018), kit 0.31.0

- Status: Proposed
- Date: 2026-10-20
- Deciders: maintainers
- Related: ADR-0053, ADR-0056, ADR-0057, ADR-0058
- Requirements: REQ-025

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

PR 8 of the K5 early scope (ADR-0053), K5 candidate 16 of the residual register. REQ-025 was taken in by intake (ADR-0056) and SPEC-0018 was Approved with its two open questions ruled (the grammar of
`Expected:`; the first commit is the earliest author date). This ADR builds it, tests first: the tests for AC1 to AC8 were written and run on unchanged `main` before any code (39 failed, 2 passed, the 2
being guards that must keep passing; the output is in the pull request body). The build was measured at about 470 lines of code and tests before it began, under the 600 of SPEC-0018 rule 10, so it is
one pull request.

## Decision

1. **The declaration** (SPEC-0018 rule 1): the three brief templates (`docs/briefs/TEMPLATE.md`, `kit/templates/playbook/brief-day.md`, `brief-overnight.md`) give each item the lines `- Size: S|M|L` and
   `- Expected: <low>-<high> hours`, and their report format asks for `Brief: <path>#<item>` and the two lines, copied unchanged, in the pull request body.
2. **The grammar** (rule 2): `common.parse_estimate(body)` returns `(size, hours)`. `Size:` is `S`, `M` or `L`; `Expected:` is `<low>-<high> hours`, two non-negative numbers (a decimal point allowed), `low`
   not above `high`, a plain hyphen. Each line once, with an optional `- ` list marker (Q-K4-214). A missing, repeated or malformed line makes both `unknown`; nothing is guessed or set to zero.
3. **The metrics** (rule 3): three columns after `hours_open_to_merge`: `actual_hours` (`merged_at` minus the earliest `commit.author.date` of `pulls/N/commits`, one decimal, round half up; `none` for a
   closed pull request; `unknown` when no commit is listed or one date is unreadable), `estimated_size` and `estimated_hours`. `hours_open_to_merge` and `cost_class` are unchanged. `size` is recorded and
   never compared with `cost_class` (rule 7).
4. **The facts** (rule 5): each pull request row gains `estimated_size`, `estimated_hours` and `actual_hours` (`null` when the pull request is not merged). `facts.py` reads `pulls/N/commits` for it and
   shares `parse_estimate` and `metrics.actual_hours`. `schema` stays 1: the fields are optional for a reader and a facts document without them reads as `unknown`. `kit/facts-schema.json` gets the three
   optional properties.
5. **The report** (rule 6): the Cost totals line ends with `; estimate: N of M within range`, M being the week's merged pull requests with a readable `estimated_hours` and `actual_hours`, N those with
   `low <= actual_hours <= high`, inclusive; with M = 0 it ends with `; estimate: none declared this week`. The same ending is on the one totals line of a busy week, before its link (Q-K4-214). Nothing else
   in the report changes. The renderer reads only the facts file and its imports are unchanged.
6. **No model, no buffer, no estimate** (rule 7): the kit counts what a person declared and what the commits show.
7. **Amendment 28** (`docs/runs/proposed-spec-amendments-28.md`) is applied to SPEC-0007 rule 8 (the supporting fields), SPEC-0009 rule 14 (the pull request row, and the body now read for the `Behaviour:`,
   `Size:` and `Expected:` lines) and SPEC-0015 rule 4 (the busy-week totals line).
8. **Tests** (`tests/kit/test_estimate.py`, `test_facts_estimate.py` and `test_product_report_estimate.py`, new; and the `ok` fixture, whose pull requests now declare an estimate and have commit dates).
9. **Kit 0.31.0**: the manifest `kit_version`, the hashes of the three brief templates and of `common.py`, `metrics.py`, `facts.py` and `product_report.py`, the plugin version and `version` in this
   repository's `agk.toml` (ADR-0050 decision 7). No file is added to or removed from the manifest.
10. **Docs**: one paragraph in the product-owner guide says what the estimate ending counts.

## Consequences

- Candidate 16 starts collecting its data from the first brief whose pull request carries the lines; a pull request without them reads `unknown` and no past record is rewritten.
- Facts read one more API list for each pull request (`pulls/N/commits`), as the metrics already do.
- The pilot gets this on its next `agk upgrade`, after its week W44 is scored on 2026-11-02.

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-214 | SPEC-0018 does not say whether a copied item line keeps its `- ` marker, where in the totals line the ending stands, or that SPEC-0009 says the body is read for `Behaviour:` only | the marker is optional; the ending is `; estimate: ...`, separated like the line's other fields and before the link; SPEC-0009's sentence is amended (amendment 28). Proposed for ruling. |

## Residual

- 2026-10-20: a check that the body's `Size:` and `Expected:` lines equal the brief item's (SPEC-0018 residual, due 2027-01-31).
- 2026-10-20: `Size` is recorded only, not compared with `cost_class` (SPEC-0018 residual, due 2027-01-31).
- 2026-10-20: author dates can be rewritten by a rebase, so `actual_hours` can move (SPEC-0018 residual, due 2027-01-31).

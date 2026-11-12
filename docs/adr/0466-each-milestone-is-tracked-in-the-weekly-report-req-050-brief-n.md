# ADR-0466: Each milestone is tracked in the weekly report

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0011, SPEC-0022, ADR-0269, ADR-0465, amendment 115 items 2 and 3, brief #1094, brief #1093, plan #661
- Requirements: REQ-050

## Context

SPEC-0043 (Approved, REQ-050, ADR-0269) rules 17 to 19 track each milestone of `docs/plan/milestones.md` against
its estimate (rules 12 to 16, `plan_estimate.py`, ADR-0465) and put a milestone at risk or late, and a plan or scope
change waiting for the person, into the weekly report without a new section. On the default branch at ba3c145 no
status script exists and the report has no milestone line. This is build (f) of rule 27.

## Decision

1. `scripts/agk/plan_status.py` (new, installed, `verbatim`) runs `--facts FILE [--plan DIR] [--today D]
   [--weeks N] [--json | --base IN --into OUT]`. Per milestone it prints `M<n> <title>` and seven lines: `briefs`,
   `hours <spent> spent of P50 <x> P85 <y>`, `forecast P50 <date> P85 <date>` (`uncalibrated` with the reasons and
   the declared sums of rule 14 on the hours line when the estimator says so), `target`, `status`, `trend` and
   `cause`; then one `waiting:` line per thing waiting; the limits line of rule 26 last. The estimate is
   `plan_estimate.py`'s own functions, imported, never computed again.
2. A brief is the milestone's by the facts' `milestone` (its `Milestone:` line), done when closed as completed;
   before any is published its brief files are its open briefs. Hours spent are the `actual_hours` of the merged
   pull requests whose `brief` is one of the milestone's briefs; one unreadable value makes the sum `unknown`.
3. The status is decided as rule 18 orders it; `late` needs a brief known to be open. The trend compares the P85
   finish with the same estimate made by `as_of`: pull requests merged before the Monday of the report's week (the
   ISO week before `--today`, as `product_report.py` takes it), briefs created before it, and briefs closed on or
   after it counted open, with `--today` the Sunday before it.
4. The causes, in rule 18's order and at most three: `waiting on review <h> h this week` (the `to_first_verdict` of
   the milestone's pull requests whose first verdict is in the report's week); `scope grew by <n> briefs` (the scope
   changes of `docs/plan/scope-changes.md` approved in the week whose `What:` names the milestone, one brief each,
   Q-1094-2); `<n> briefs stalled (builder)` (its open pull requests whose `stalled` is true; the facts name no
   other kind); `<n> of <m> estimates missed` (merged, actual above the declared high). Unreadable pull requests
   make the cause `unknown`.
5. What waits for the person: the plan while `docs/plan/baseline.json` is absent (rules 8 and 20), and each scope
   change whose `Status:` is `proposed` and that has no `Approved:` line (rule 22).
6. `--base IN --into OUT` writes `IN` with one more top-level key `plan`, the `--json` data. `kit/facts-schema.json`
   gains `plan` as an optional property (amendment 115 item 1); the facts' `schema` stays 1.
7. `scripts/agk/product_report.py` reads `plan` when it is there: a milestone `at risk` or `late` is one item of
   the new kind `milestone-at-risk` in At risk; the new groups `scope-change` and `plan` of Needs you and of the
   inbox hold the kinds `scope-change-waiting` and `plan-waiting`, after the seven groups of today. A `plan` that is
   not an object is one `unknown` item. Without `plan` no item changes, so every `report.md` golden is
   byte-identical; `REPORT_SCHEMA` and `kit/report-schema.json` rise from 8 to 9 (amendment 115 item 2, which named
   3 to 4 when it was written). The report computes no estimate: it prints what the facts carry (amendment 115
   item 3).
8. The `product-report` workflow gains one step, committed by the owner on this branch (Q-1094-1, builders never
   change a workflow): when `docs/plan/milestones.md` exists it makes the plan's facts with `facts.py --weeks 12` and
   runs `plan_status.py --facts PLAN --weeks 12 --base IN --into OUT` before the report; `OUT` replaces the report's
   facts file, so the report reads one file and the uploaded `facts.json` is `OUT`. A project without a plan runs
   neither command.

Protected path classes changed: `.github/` (`.github/workflows/product-report.yml`, the one step of decision 8),
`scripts/agk/` (`plan_status.py`, new; `product_report.py`), `kit/`
(`kit/manifest.json`, `kit/facts-schema.json`, `kit/report-schema.json`, and `kit/hashes.json` only as
`kit_hashes.py` prints it), `agk.toml` (two `[[testing.map]]` entries), `tests/kit/` (`test_plan_status.py`, new; the report goldens'
`schema`, one new report fixture and the tests that pin the schema to 8) and `tests/kit_dev/`
(`test_facts_wiring.py`, which alone may name the facts schema, validates the `plan` key).

## Consequences

A project with a plan sees, each week, which milestones are at risk or late and why, measured, and what waits for
its confirmation. A project without a plan sees the same report text; only the report data's schema number rises.

## Residual

- 2026-11-12: the facts list only the briefs closed in their own `--weeks` window, so a milestone's done count leaves
  out briefs closed before it (due 2026-12-31).

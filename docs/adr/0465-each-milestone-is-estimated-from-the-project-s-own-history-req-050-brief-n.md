# ADR-0465: Each milestone is estimated from the project's own history

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, ADR-0269, ADR-0456, ADR-0457, amendment 115 item 1, brief #1093, brief #1075, plan #661
- Requirements: REQ-050

## Context

SPEC-0043 (Approved, REQ-050, ADR-0269) rules 12 to 16 estimate each milestone of `docs/plan/milestones.md` as a
calibrated range from the project's merged pull requests and weekly throughput, print the inputs, and print
`uncalibrated` rather than a guess. Amendment 115 item 1 has the facts list each brief issue, open or closed in the
window, with its state, close and plan lines. On the default branch at 8efe023 no estimator exists and `facts.py`
lists open briefs only. This is build (e) of rule 27; build (c) (brief #1075, ADR-0456) defines the plan files.

## Decision

1. `scripts/agk/plan_estimate.py` (new, installed, `verbatim`) runs `--facts FILE [--plan DIR] [--today D]
   [--weeks N]` as rules 12 to 16 say: the window's first Monday is `facts.window_start` and the `Size:` and
   `Expected:` grammars are `common.ESTIMATE_LINES`, both imported; `random.Random("hours:M<n>")` and
   `random.Random("weeks:M<n>")`, 10,000 trials, nearest-rank positions 5000 and 8500; `uncalibrated` with every
   reason that applies, joined by `; `, the declared sums and `finish unknown`; the three wait medians on their own
   line, never added, and `queue unknown`; one `inputs:` line after each milestone; the limits line of rule 26 last.
2. A milestone's open briefs are the facts' briefs whose `milestone` names it and whose `state` is `open`, by issue
   number; when the facts hold none for it (nothing published yet), its brief files `<plan>/briefs/M<n>/<key>.md`, by
   key (rule 13's "by key before publish").
3. An input that cannot be read is never counted as 0: `pull_requests` `unknown` prints `history unknown`, and
   `flow.briefs` `unknown` prints `M<n> <title>: unknown (the facts' briefs cannot be read)`. A facts file, plan
   folder, `--today`, `--weeks` or `[plan]` setting that cannot be read exits 2 naming the option or setting.
4. In the `inputs:` line `review` is the median `to_first_verdict` and `merge` the median `cleared_to_merge`;
   `verdict_to_cleared` is on the waits line (rule 15). A trial that draws 520 weeks makes the dates `unknown`.
5. `scripts/agk/common.py` gains `plan_settings` (`[plan]`: `iteration_days` 1 to 30, 10; `calibration_min`
   positive, 10; `default_hours`, a table of `S`, `M`, `L` to `"<low>-<high>"`, empty; any other key or value refused
   naming the setting) and `estimate_parts`, which reads `Size:` and `Expected:` apart, so a brief with a size and
   no range keeps its size. `kit/templates/agk.toml`, `kit/templates/agk.adopt.toml` and `agk.toml` carry the table
   commented out.
6. `scripts/agk/facts.py` lists, beside the open briefs, the briefs closed in its `--weeks` window, each with
   `state`, `closed_at`, `state_reason` (`completed`, `not_planned` or `unknown`; null when open), `milestone` (a
   single `Milestone: M<n>` line, or null), `size` and `expected` (amendment 115 item 1); `schema` stays 1 and
   `kit/facts-schema.json` gains the six optional properties. `scripts/agk/product_report.py`, the one reader of
   `flow.briefs`, keeps only `state` `open` (a missing `state` reads as open), so its output does not change; the
   amendment assumed that filter already held.

Protected path classes changed: `scripts/agk/` (`plan_estimate.py`, new; `facts.py`; `common.py`;
`product_report.py`), `kit/` (`kit/manifest.json`, `kit/facts-schema.json`, `kit/templates/agk.toml`,
`kit/templates/agk.adopt.toml`, and `kit/hashes.json` only as `kit_hashes.py` prints it), `agk.toml` (the commented
table and one `[[testing.map]]` entry) and `tests/kit/` (`test_plan_estimate.py`, new).

## Consequences

A project with a plan can see, for each milestone, a P50 and P85 of hours and finish dates that a person can check
from the printed inputs, or `uncalibrated` with the reason while its history is short. A project without a plan
sees no change: the report counts the same open briefs.

## Residual

- 2026-11-12: a brief whose `Milestone:` line names something other than `M<n>` (for example a wave) has no
  milestone in the facts (due 2026-12-31).
- 2026-11-12: the facts fetch the comments of every brief issue, open or closed, as before; only the listing grows
  (due 2026-12-31).

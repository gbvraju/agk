# ADR-0269: Add REQ-050: A project's plan is drafted from its sources and tracked with calibrated ranges

- Status: Proposed
- Date: 2026-11-04
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0009, SPEC-0011, SPEC-0012, SPEC-0013, SPEC-0018, SPEC-0034, SPEC-0037, SPEC-0038, SPEC-0040, ADR-0153
- Requirements: REQ-050

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-04:

> From a project's source documents (SOW, BRD, PRD, design links), AGK drafts the scope, milestones, requirements, specs and briefs with traceability to each source line, estimates every milestone as a calibrated range, tracks the plan against actual progress with a forecast and controlled scope change, and runs the plan in phases with agile ceremonies (planning, daily status, review, retrospective).

The brief is issue #539; the conductor reserved REQ-050, SPEC-0043, this ADR number and proposed
spec amendment number 115 for it (the field note on #539). The owner's direction of 2026-11-04,
quoted as data, is recorded as one row of `docs/runs/decisions-log.md`: "When developer start the
project they might having the SOW or BRD, PRD or Design figma URLs, how our AGK can help them to
create Milestones, issues or specs, brief as it calls and define the scope and make sure it is
moving as per the plan. We need clear realistic estimations for Milestone with AGK. So it will also
adopt the phase of work and work similar to Agile ceremonies."

Today a project starts from one problem statement (`/agk:start`, SPEC-0013) or one sentence at a
time (`/agk:spec`, SPEC-0012); a brief declares `Size:` and `Expected:` and the metrics compare them
with `actual_hours` (SPEC-0018), but the kit makes no estimate (SPEC-0018 rule 7), and nothing
reads a project's source documents, forecasts a milestone or controls a change of scope.

## Decision

1. REQ-050 is added to `docs/requirements.md` as `planned`, with eight criteria each testable with
   invented sources and saved facts. SPEC-0043 is added as `Draft`. Merging this pull request
   approves the requirement as a proposal; it does not approve the spec, which stays `Draft` until
   the owner's own `Approve: SPEC-0043` line approves it.
2. Sources are the person's: Markdown or text under `docs/sources/` with a header, design links as
   rows with a version and named frames, read only after the data guard of brief #538 and never
   fetched by a check (SPEC-0043 rules 1 to 3).
3. A skill drafts proposals as data and a standard-library script validates and renders them, every
   item citing a source location that exists, nothing invented, conflicts listed for the person, and
   nothing created on GitHub or in the forge before the person's `Approve: plan <head>`. The script
   never edits `docs/requirements.md`: requirements enter through intakes (rules 4 to 8).
4. A milestone's estimate is a range, P50 and P85, from a seeded simulation over the project's own
   history (`actual_hours` per size, throughput per week), `uncalibrated` below a minimum, with its
   inputs printed and no wait counted twice; the metrics, the Cost line and `product_report.py`
   compute no estimate (rules 12 to 16 and 26). Status, forecast, trend and cause go into the
   existing report's At risk and Needs you sections; a project without a plan sees no change
   (rules 17 to 19). Scope changes only by an approved record against a baseline that is never
   rewritten (rules 20 to 22). Iterations and four ceremony outputs are printed for the person;
   AGK runs no meeting and posts nothing (rules 23 and 24).
5. Approved specs change only by `docs/runs/proposed-spec-amendments-115.md`: SPEC-0009 (the facts
   carry every brief and the `plan` key), SPEC-0011 (the At risk line, the inbox kinds, the report
   step, `report.json` kinds), SPEC-0018 rule 7 (narrowed to the metrics and the report), and the
   planning guide. This pull request applies none of them; builds (e), (f) and (j) do.
6. The builds (b) to (j) of SPEC-0043 rule 27 will change these protected path classes:
   `scripts/agk/` (`check_plan.py`, `plan_intake.py`, `plan_estimate.py`, `plan_status.py` and
   `plan_ceremony.py`, new; `facts.py`, `product_report.py` and `common.py`), `skills/`
   (`skills/plan-intake/SKILL.md`), `kit/` (`kit/manifest.json`, `kit/report-schema.json`,
   `kit/templates/agk.toml` and `kit/templates/agk.adopt.toml`, a commented `[plan]` table),
   `agk.toml` (the same commented table), `.github/` (one step in each of the existing
   `governance.yml` and `product-report.yml`; no new workflow), `agk.mk` (the governance step),
   `tests/kit/` and `tests/kit_dev/` (their tests). Whether a new skill also needs a line in
   `.claude-plugin/` is `(verify)`, read by build (c). Each build adds its own ADR naming the
   classes it changes and citing this one (`Q-S0043-18`). No build changes `constitution/`,
   `config/`, `.claude/`, `CLAUDE.md`, `Makefile` or `pyproject.toml`.
7. The builds that read sources declare `Depends-on` the builds of brief #538 that add the data
   guard (`scripts/agk/guard.py` and `.claude/hooks/data_guard.py`), which has no off switch, so
   `plan_intake.py` refuses when it is not installed and runs `guard.scan_text` on each source first, and build (i) the build of brief #536 that adds the file forge. This pull request changes
   documents only and declares no dependence: the brief's `Depends-on: #538` is for the builds
   (the field note on #539).

## Consequences

The requirement is listed as planned, and the spec and this ADR wait for the owner's approval.
Nothing is delivered until the builds merge. No check, flow or setting changes in this pull
request, and a project without `docs/plan/` sees no change from any build.

## Residual

None. The intake checks cannot tell whether the calibration minimum, the simulation or the status
rule are the right ones; that is the review of this pull request and the owner's rulings on
`Q-S0043-1` to `Q-S0043-19`.

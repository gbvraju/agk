# ADR-0461: A validated plan is rendered once, as new draft files the person owns

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0034, SPEC-0030, SPEC-0018, ADR-0269, ADR-0454, ADR-0456, ADR-0457, amendment 163, brief #1081, plan #661
- Requirements: REQ-050

## Context

SPEC-0043 (Approved, REQ-050, ADR-0269) rule 7 turns a validated proposals file into the plan's draft files. Build (c1)
(brief #1075, ADR-0456, merged as #1087) gave `plan_intake.py validate` and `states`; this build, (c2), is `render`.
Rule 7 names three readings that pull against each other: a rendered brief's `Advances:` names its requirement's key
until the requirement has a `REQ-n` number, build (d)'s `check_plan.py` (ADR-0457) reads those keys from the brief
files for the trace, and `check_brief.py` accepts only `Advances: REQ-n` or `Advances: new` and `Depends-on: #n`.
`new_spec.py`, whose `make_spec` rule 7 names, is kit-only (not in `kit/manifest.json`), while `plan_intake.py` is
installed.

## Decision

1. `python3 scripts/agk/plan_intake.py render --proposals FILE [--root DIR]` runs `validate` first, with its guard gate
   and its source scan (rule 3), and refuses with exit 1, printing `validate`'s lines, a file that `validate` fails.
2. Before it writes anything it prints `Conflicts for the person` with every conflict (`- <location> <location>:
   <description>`, and `(Settled: <location>)` when settled), then `Open questions for the person` with every item of
   `scope.open_questions` (`- <text> (<locations>)`) (rule 6, amendment 163 item 5); an empty list prints `- none`.
3. It writes, as new files only: `docs/plan/scope.md` (the five lists of rule 4 under `## In scope`, `## Out of scope`,
   `## Assumptions`, `## Constraints` and `## Open questions`, one line per item ending with its locations in
   backticks), `docs/plan/milestones.md` (`### M<n> <title>` with `Exit:`, `Acceptance:`, `Target:` (the date, or
   `(verify)` when the proposals hold `null`) and one `Source:` line per location), `docs/plan/requirements-proposed.md`
   (`### <key> <title>`, the criteria, `Milestone:`, `Status: planned` and one `Source:` line per location), one Draft
   spec per area through `new_spec.make_spec` (imported, not copied; the area's name is the title and its requirement
   keys are in the spec's proposal text) and one brief per brief in `docs/plan/briefs/M<n>/<key>.md`.
4. All or nothing: when any of those files exists, or the spec template cannot be read, it refuses with exit 1 naming
   the rule and the path, and writes nothing. It never edits `docs/requirements.md`.
5. A rendered brief holds `Sentence:` (its title), `Answers` (one numbered item per requirement it advances, with that
   requirement's criteria), `Advances:` (the requirement keys), `Touches:`, `Size:`, `Expected:`, `Milestone:`, one
   `Depends-on: <key>` line per dependence, `Contexts:` (each context `(verify)`, for the person to state) and one
   `Source:` line per location. The keys on `Advances:` and `Depends-on:` are the only lines that `check_brief.py`
   fails as rendered; the person or rule 25's `publish` replaces them with `REQ-n` and `#n`, after which the brief
   passes. No `Priority:` line is written: the proposals carry no priority, and rule 2 of SPEC-0034 allows none.
6. A brief that could never pass `check_brief.py` or that would leave its folder is refused, naming the rule and its key:
   a key that is not a file name (`[A-Za-z0-9][A-Za-z0-9._-]*`), an empty `touches` or `advances`, or a title over 300
   characters; and an area whose name has no letter or digit, which `new_spec.slug` cannot name. Text values are written on one line each (runs of white space become one space).
7. `new_spec.py` is imported when `render` runs. The skill runs `plan_intake.py` from the plugin's root, where
   `new_spec.py` lies beside it; an installed copy without it exits 2 with `render needs new_spec.py:
   scripts/agk/new_spec.py`, naming the path.

Protected path classes changed: `scripts/agk/` (`plan_intake.py`) and `tests/kit/` (`test_plan_render.py`).
`kit_hashes.py` leaves `kit/hashes.json` unchanged.

## Consequences

A person turns a validated proposals file into a plan they can read and edit, with every disagreement between the
sources shown before a file exists, and nothing written over their own edits. The trace of build (d) reads the
rendered files as they are.

## Residual

- 2026-11-12: rendered briefs fail `check_brief.py` on their key lines until the keys are numbered (`Q-1081-1`); rule 25's
  `publish` (build (i)) replaces them (due 2026-12-31).
- 2026-11-12: the `Contexts:` line of a rendered brief is `(verify)` for each context until the person states it
  (due 2026-12-31).

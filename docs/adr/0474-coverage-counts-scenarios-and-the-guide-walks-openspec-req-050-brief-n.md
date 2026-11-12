# ADR-0474: The plan's coverage counts OpenSpec scenarios, and the planning guide walks an OpenSpec file to a plan

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, ADR-0269, ADR-0472, ADR-0473, ADR-0457, ADR-0460, amendment 166, amendment 163, brief #1110,
  brief #1109, brief #1079, plan #661
- Requirements: REQ-050

## Context

Amendment 166 (ADR-0472) item 5 has rule 11 count scenarios beside source lines and, with an imported prototype, list
each scenario that names no mapped screen and each mapped screen that no scenario names. Build (a), brief #1109
(ADR-0473), imports an OpenSpec file and reads it into a proposals file whose acceptance lines end with each scenario's
location; its residual leaves item 5 to this build. On the default branch `check_plan.py` counts in-scope source lines
and screens only, and `docs/guides/planning.md` names no OpenSpec step.

## Decision

1. When `docs/sources/` holds a `Kind: openspec` source, rule 11's line gains, after its first count,
   `<a> of <b> scenarios have an acceptance line and <c> a test`; without one the line is as before.
2. A scenario is a `Scenario: ` heading, at any level, under a `Requirement: ` heading of a `Kind: openspec` `.md` file
   whose path has no `changes` part, in a combined file only under a capability (a heading followed by its
   `*Capability ` line), as `plan_intake.py openspec` reads it. Its location is the one that reading writes:
   `<file>#<heading>`, or `<file>:<line>` when the heading repeats in its file.
3. A scenario has an acceptance line when a line of a requirement block of `docs/plan/requirements-proposed.md` or
   `docs/requirements.md` ends with ` (<its location>)`, and a test when the id of such a block has a test marker
   (`common.markers_for`, the reading of `traceability.py`). The test count reads local files only, so it is printed
   without `--facts`.
4. With `--trace` and a `Kind: design` source, after the matrix, each scenario is one line
   `info plan: scenario <location>: <screen locations>` or `info plan: scenario <location>: names no screen`, and each
   `<screen>/<state>` heading no scenario names is one line `info plan: screen <location>: no scenario names it`. A step
   (`GIVEN`, `WHEN`, `THEN` or `AND`) names a screen when it holds the screen part of the heading as whole words, case,
   hyphens and underscores aside; it then names every state of that screen. The lines are information and never fail
   the check, until the person confirms the plan.
5. `docs/guides/planning.md` gains the section `From a prototype and an OpenSpec file`: import the prototype and its
   source, `openspec-import`, `openspec`, `/agk:plan-intake`, `validate`, `render`, `check_plan.py --trace`,
   `Approve: plan` and `publish`, in that order, with the sentence that a customer's file is processed only where the
   customer's contract allows it and never enters the kit's repository; its rule 1 kind list names `openspec`.

Protected path classes changed: `scripts/agk/` (`check_plan.py`) and `tests/kit/` (`test_check_plan_trace.py`,
`test_guide_planning.py`).

## Consequences

A person planning from an OpenSpec file sees how many of its scenarios reached an acceptance line and a test, and which
scenarios and screens of the prototype do not meet, before confirming the plan. A project without an OpenSpec source sees
the same output as before. Nothing is written and nothing opens the network.

## Residual

- 2026-11-12: a screen is matched by its name in a step's words only; a scenario that names a screen by another word
  (a synonym, a page title) is listed as naming no screen, for the person to read (due 2026-12-31).
- 2026-11-12: the unmatched lists are information; whether they become failures after `Approve: plan` is the
  maintainers' to rule (due 2026-12-31).
- 2026-11-12: the amendment's rule text is not written into SPEC-0043 here, since the brief's `Touches:` does not name
  the spec (due 2026-11-30).

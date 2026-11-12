# ADR-0462: The plan names personas and writes each requirement as a user story

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, ADR-0269, ADR-0454, ADR-0456, ADR-0457, ADR-0461, ADR-0469, amendment 163, amendment 164,
  brief #1090, brief #1089, brief #1081, brief #1076, plan #661
- Requirements: REQ-050

## Context

Amendment 164 item 2 (ADR-0469, approved by the owner's `Approve:` lines for SPEC-0043 on #1097) adds personas and user
stories to SPEC-0043 rules 4 to 7 and 9. On the default branch at 7ffd070 the proposals of `plan_intake.py` (ADR-0456)
hold `scope`, `milestones`, `requirements`, `areas`, `briefs` and `conflicts`, a requirement names no user it serves,
`render` (ADR-0461) writes no personas, and the trace of `check_plan.py --trace` (ADR-0457) has no persona column. This
is build (p).

## Decision

1. The proposals hold `personas`, a required top-level key after `scope`: each item `key` (`P1`, `P2`, ... in order),
   `name`, `goals` (a non-empty list of plain sentences) and `sources` (non-empty locations of rule 1, which resolve as
   every item's do). Each requirement also has `persona` (a persona's key) and `story`. The `schema` stays 1.
2. `validate` refuses, naming the rule and the item's key, never its text: a missing `personas`, a persona or a
   requirement with a missing or unknown key (rule 4), a persona key out of order (rule 4), an empty `goals` or
   `sources` (rule 4), a `persona` that names no persona (rule 5), and a story that does not start
   `As <the persona's name>, I want ` or has no `, so that ` after that, which is the form only (`Q-1089-4`) (rule 5).
3. A user that the sources only imply is a `scope.open_questions` item with `(verify)`, which rule 6 already requires and
   `render` already prints under `Open questions for the person`; the skill `/agk:plan-intake` says so and never makes
   up a persona.
4. `render` writes, beside its other new files and all or nothing, `docs/plan/personas.md`: `# Personas`, one line on who
   drafted it, then per persona `### P<n> <name>`, one `Goal:` line per goal and one ``Source: `<location>` `` line per
   location (the backticked form the plan's other files use). Each block of `docs/plan/requirements-proposed.md` gains
   `Persona: P<n> <name>` and `Story: <story>` after its heading and before `Criteria:`.
5. `check_plan.py` rule 10 fails a block of `docs/plan/requirements-proposed.md` whose `Persona:` key no `### P<n>`
   heading of `docs/plan/personas.md` holds, naming the requirement and the key. A block without a `Persona:` line, as a
   plan rendered before this build has, is not failed. The trace (rule 9) has a `Persona` column after `Requirement`:
   the `Persona:` keys of the row's requirements, `none` where they have none (`docs/requirements.md` has none).

Protected path classes changed: `scripts/agk/` (`plan_intake.py`, `check_plan.py`), `tests/kit/`
(`test_plan_personas.py`, and the fixtures of `test_plan_intake.py`, `test_plan_render.py` and
`test_check_plan_trace.py`), `tests/kit_dev/` (`test_plan_intake_skill.py`) and `skills/` (`plan-intake/SKILL.md`).

## Consequences

A plan drafted from a project's sources says who each requirement serves, as a story a person can read, and the trace
shows that person beside the source line. A proposals file written before this build fails `validate` with
`missing key personas` until the person or the skill adds them; a plan already rendered is not failed by `check_plan.py`.

## Residual

- 2026-11-12: the amendment places a requirement without `persona` or `story` under rule 5; `validate` reports it as
  rule 4's `missing key`, as for every missing field (`Q-1090-1`) (due 2026-11-30).
- 2026-11-12: the texts of SPEC-0043 rules 4 to 7 and 9 are not written into the spec here; the brief's `Touches:` does
  not name the spec, as for build (q) (`Q-1091-2`) (due 2026-12-31).
- 2026-11-12: the story's capability and outcome are the person's to judge; only the form is checked (`Q-1089-4`)
  (due 2026-12-31).

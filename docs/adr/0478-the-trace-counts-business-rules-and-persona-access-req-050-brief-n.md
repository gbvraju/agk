# ADR-0478: The plan's trace counts business rules and persona access

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, ADR-0269, ADR-0462, ADR-0473, ADR-0474, amendment 167, amendment 166, amendment 164, brief #1118,
  plan #661
- Requirements: REQ-050

## Context

A plan drafted from a prototype and an OpenSpec file counts source lines, screens and scenarios (ADR-0474), but one
OpenSpec requirement often holds several business rules, and nothing records which persona may use which screen. The
owner asked that checks prove "Tests and every persona's access", without over-engineering. Amendment 167 proposes two
items; this pull request carries the amendment and its build.

## Decision

1. Each sentence of a requirement's statement holding `SHALL` (`SHALL NOT` included) is one rule, keyed
   `<requirement key>.r<n>`; an acceptance line names the rules it proves with `(rules r1, r2)`. `plan_intake.py
   validate` refuses a mark naming a rule the statement does not hold.
2. The plan draft may hold `access`, cells `{persona, screen, allowed, sources}`: a persona key, a screen of
   `docs/design/inventory.md`, `yes` or `no`, and at least one source; one cell per persona and screen. An acceptance
   line names a cell with `(access <persona>/<screen>)`; each `no` cell needs one. `render` writes
   `docs/plan/access.md` when `access` is not empty.
3. `check_plan.py --trace` prints `info plan: <a> of <b> rules have an acceptance line and <c> a test` with the rules
   that have none, and `info plan: <a> of <b> access cells have a test` with the cells that have no acceptance line; a
   test is a `REQ-nnn ACn` marker for the naming criterion, read with `--facts`, else `not read`, as ADR-0474 decision 3.
   The lines are information and never fail the check.

Protected path classes changed: `scripts/agk/` (`plan_intake.py`, `check_plan.py`) and `tests/kit/`
(`test_plan_intake.py`, `test_check_plan_trace.py`).

## Consequences

A person sees, before confirming a plan, which business rules and which persona-screen cells have no acceptance line or
no test. A plan without a statement or an access table prints what it printed before. No test is generated; nothing
opens the network.

## Residual

- 2026-11-12: the amendment's text is not written into SPEC-0043 here, since the brief's `Touches:` does not name the
  spec (due 2026-11-30).
- 2026-11-12: the `plan-intake` skill does not yet fill `access`; a brief follows (due 2026-12-31).
- 2026-11-12: whether the lines fail after `Approve: plan` is the maintainers' to rule (due 2026-12-31).

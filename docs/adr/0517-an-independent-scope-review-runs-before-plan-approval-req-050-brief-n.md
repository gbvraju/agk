# ADR-0517: An independent scope review runs before plan approval

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0043, ADR-0459, brief #1218, plan #661
- Requirements: REQ-050

Protected classes: `skills/`, `tests/kit_dev/`

## Context

In a customer trial the only check that found missing scope in a drafted plan was a review the owner asked for by hand,
in a fresh session told not to read the plan's own scope files: it found about 570 gaps and 16 conflicts that the
plan's own trace and coverage counts did not show, because those counts read the plan's own files. The kit had no
command for that review, so each project would have to invent the prompt.

## Decision

1. A plugin skill `/agk:scope-review` (`skills/scope-review/SKILL.md`, model invocation off, run by the person) runs in
   a fresh session. It never reads `docs/plan/scope.md`, `docs/plan/prototype-coverage.md` or a planning report (the
   proposals file of `/agk:plan-intake`, a plan walk or a render's output). It runs the data guard
   (`plan_intake.py states`) before any source is read, then compares every `docs/sources/` file and every imported
   design version (`docs/design/imported/i<n>/`) with `docs/requirements.md` and `docs/plan/briefs/`.
2. Step 1 writes one report at a path the person names outside `docs/`, never committed: per source, each screen,
   state, field, rule, role or requirement that nothing covers, with its location, and each conflict with both sides
   and their locations. Step 1 changes no file in the repository.
3. Step 2 runs only when the person asks for it after reading the report. Each finding becomes one of four outcomes:
   covered (with its requirement), gap (a proposed requirement and brief in the milestone of its area), out of scope
   (with its source) or decision (both sides and a recommendation), written to `docs/plan/scope-triage.md` and to no
   other file. The gaps' requirements and briefs enter the plan the usual way (the person's intake), never by this skill.
4. `docs/guides/planning.md` orders the review before `Approve: plan` in both of its paths.

## Consequences

Every project gets the same review prompt, and the approver reads a report made without the plan's own view of its
scope before approving. The review is advisory: no check reads the report or the triage file, and the gate stays the
`Approve: plan` line.

## Residual

- 2026-11-14: "a fresh session" is an instruction the skill gives and cannot verify; a later build may record the
  session that wrote the report (due 2027-01-31).

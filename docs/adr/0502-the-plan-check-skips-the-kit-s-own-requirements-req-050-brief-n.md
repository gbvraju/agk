# ADR-0502: The plan check skips the kit's own requirements

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: brief #1183, plan #661, ADR-0457
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

`init.py` installs `docs/requirements.md` with the kit's REQ-001, REQ-002 and REQ-003; the file reserves REQ-001 to
REQ-099 for the kit, and these blocks carry no `Source:` line. Rule 10 of the plan check (ADR-0457) fails every
requirement block with no `Source:` line that resolves. In the co-owner's trial of 2026-11-13, once `docs/plan/` existed,
`check_plan.py` failed rule 10 on REQ-001, REQ-002 and REQ-003 while 5 of 5 in-scope source lines had a requirement, so
`make governance`, prepush and the governance workflow were red on the project's first plan pull request for lines the
person never wrote.

## Decision

1. A block of `docs/requirements.md` numbered REQ-001 to REQ-099 with no `Source:` line is a kit requirement: rule 10's
   `Source:` test, the trace and every count of rule 11 leave it out, and the trace prints no row for it.
2. A block of that range that carries a `Source:` line is checked as any other, and so is every block outside the range
   (a REQ-101 with no `Source:` line, or with one that does not resolve, still fails).
3. `docs/guides/planning.md` step 7 says so in one sentence.

## Consequences

A project that plans with AGK passes governance on its plan pull request when its own requirements trace to sources.
The kit's requirements no longer lower the `requirements have a brief` and `requirements have a test` counts. A project
that numbers its own requirement inside the kit's range without a source is not failed; the template of
`docs/requirements.md` already tells it not to use that range.

## Residual

- 2026-11-13: none.

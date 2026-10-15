# Proposed spec amendments 5 (SPEC-0004)

Date: 2026-10-15 (from `date -u`). Found while carrying out the residual backfill of Q-ON-14 (day-7 brief, item 1).
Approved specs change only through a proposal like this one (principle 6). Nothing here is applied; maintainers decide.

## Problem

SPEC-0004 rule 9 (D4) reads `(due YYYY-MM-DD)` on `## Residual` bullets of ADRs and specs. An Accepted ADR cannot change
except its Status line (principle 6, `check_adrs`), and an Approved spec changes only through an amendment file, so the
existing residuals can never receive a due date, and D4 would find nothing for them.

## SPEC-0004 (`docs/specs/0004-drift-audit.md`)

1. **Rule 9, the residuals register.** Now: "A `## Residual` bullet of an ADR or spec that carries `(due YYYY-MM-DD)`
   with a date before the run date. ..." Proposed: add "D4 also reads `docs/runs/residuals.md`: each line of its
   `## Open` section has the form `- <source> | <text> | (due YYYY-MM-DD) | <status>`; a line whose date is before the run
   date is a finding naming its source. A bullet in a new ADR or spec carries its own `(due YYYY-MM-DD)`; the register
   exists for bullets of Accepted ADRs and Approved specs, which cannot change. A malformed line in the `## Open` section is
   reported as a finding, not skipped."
2. **Rule 18 fixtures.** Add a fixture: a register line past its date (found), one in the future (not found), a
   malformed line (found).
3. **Register upkeep.** `docs/runs/residuals.md` is a docs file; changing it needs no ADR. A line leaves `## Open` when
   the residual is resolved, by a maintainer-reviewed PR that cites the resolving PR.

## The draft register

`docs/runs/residuals.md` is in this PR: 19 open lines (one per residual, the substring-matching
residual of ADR-0003 counted once for the five ADRs that repeat it) and 8 closed ones. The due dates are my
proposals.

## Questions

- Q-K2-15: confirm the closed list (or say which lines stay open).
- Q-K2-16: ADR-0001's `github_team` residual said "replace by K1 exit". I cannot see GitHub teams, so I left it out of both
  lists as unknown: is it resolved?
- Q-K2-17: is `docs/runs/residuals.md` the right place, or should the register be `docs/residuals.md`?

## Status

Applied 2026-10-15 on maintainers' instruction (final commit of the item 1 PR). SPEC-0004 rules 9 and 18 carry
the proposed text; amendment 3 (upkeep) is a practice, not spec text. Q-K2-15 and Q-K2-17 were answered by the
maintainers: the closed list is confirmed and the register stays at `docs/runs/residuals.md`; Q-K2-16 was answered
by adding ADR-0001's residual to the closed table.

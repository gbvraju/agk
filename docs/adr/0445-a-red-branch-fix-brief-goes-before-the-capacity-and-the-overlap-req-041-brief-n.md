# ADR-0445: A red branch's fix brief goes before the capacity and the overlap (REQ-039, REQ-041)

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: SPEC-0032, ADR-0414, brief #1052, brief #962, plan #661, alarm #1049, brief #1048, pull request #1045
- Requirements: REQ-039, REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`, `docs/adr/`

## Context

On 2026-11-11 the default branch went red at 08:04Z. The conductor filed fix brief #1048 and named
it on alarm #1049 with `fix brief filed: #1048`. `session.py plan` printed `Start 0: no brief is
ready.` and `#1049 is fixed by #1048.`, because while the branch is red `survey` keeps only the
router's alarm, which ADR-0414 then hides as fixed; and `session.py claim --brief 1048` refused it
for overlapping open pull request #1045. Nothing could start until the owner ruled, more than four
hours later.

## Decision

1. One function, `session_plan.fix_briefs`, names a red branch's fix briefs for `survey`, `plan`,
   `next` and `claim`: the open brief that ADR-0414's rule names as the fix (`fixed_by`) of an open
   red alarm (`session.is_red`), the lowest number of what names it. A pull request that is the
   lowest names no fix brief. `red_fixes` and `fix_briefs` share that rule (`fix_briefs_of`).
2. While the branch is red, `survey` keeps each fix brief beside the alarm, in `Survey.fixes`. It
   reads the open pull requests only when a brief or a listed author's `fix brief filed:` names a
   fix, so a red survey with none still reads no pull request, and a take of a fix brief lives
   while its open pull request does.
3. The plan chooses a fix brief without the overlap (`waves`), with at least one slot, and keeps
   `#<red> is fixed by #<n>`; `next` offers it without the overlap; `claim` takes it without
   `claim_overlap`. The owner's hold (`Hold:`), the shape check, the reservation and a live take by
   another session still apply.
4. Nothing else changes: every other brief waits while the branch is red, and once the branch is
   green a former fix brief is judged by the overlap as before. The open pull request it overlaps
   merges the default branch after the fix merges, as now.

## Consequences

A red branch is fixed without a person's ruling when its fix overlaps open work. Two assertions of
ADR-0414's tests (`test_plan_holders.py`) that expected no assignment now expect the fix brief, as
answer 2 of brief #1052 requires; the alarm itself is still not assigned. `merge_cleared.red_fix`,
`config/session-rules.md` and the role files are unchanged.

## Residual

- 2026-11-11: none.

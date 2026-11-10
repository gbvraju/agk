# ADR-0414: The plan does not assign a red-branch alarm that a fix already names (REQ-039, REQ-041)

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: SPEC-0032, brief #962, plan #661, issue #953, brief #955
- Requirements: REQ-039, REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

On 10 Nov the default branch went red and the router opened alarm #953. The conductor filed fix
brief #955 and its builder opened a pull request, yet `session.py plan` still printed an `Assign`
line for #953, so a second slot would have built the same fix. Brief #962 asks that one red head
get one fix.

## Decision

`session_plan.build` drops from the ready briefs an open issue titled `RED_TITLE` when a fix for it
is open: an open `agk-brief` issue (not itself a red alarm) or an open pull request whose body has
`#<red>` in a line starting `Fixes`, `Closes`, `Red:` or `Plan:` (case aside), or a line holding
`for issue #<red>`, with the whole number only; or a comment on the alarm by a listed verdict author
saying `fix brief filed: #<n>` where `#<n>` is an open `agk-brief` issue. The alarm is then listed
under the plan's waits as `#<red> is fixed by #<n>`, the lowest such number. While the branch is
red the survey reads no pull request, so the plan reads the open ones only when an alarm is ready.
A red alarm with no fix is assigned as before; the red-branch path of SPEC-0032 rule 9 is kept.
The tests are in `tests/kit/test_plan_holders.py`, marked `REQ-039` and `REQ-041`.

## Consequences

The conductor's `Assign` lines no longer send a slot to an alarm that is already being fixed.
`session.py next` is unchanged (Q-962-1). A plan that cannot read the open pull requests while an
alarm is ready stops with the existing `rule 1` refusal rather than guessing.

## Residual

- 2026-11-10: whether `session.py next --take` should skip a fixed alarm too is Q-962-1.

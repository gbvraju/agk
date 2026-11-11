# ADR-0437: A release with a reason frees the take

- Status: Accepted
- Date: 2026-11-11
- Deciders: maintainers
- Related: brief #1026, plan #661, brief #842
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

On 2026-11-10 brief #842 build (c) was assigned to s3, but s4 had taken it and gave it back four times, each time as
`released: s4` followed by a blank line and a sentence of reason. `session.all_takes` read a release with
`RELEASED.fullmatch` over the whole comment body (after `plain`), so text after the `released:` line made the comment
no release, the take stayed live for `claim_hours` and the assigned slot could not take the brief. Measured on main
f3b25f4 with the brief's `Measured:` command: `[False]` for the reasoned release, `[True]` for a bare one.

## Decision

1. `session.all_takes` reads a `released: <session> [build (<x>)]` comment from its first line alone, after `plain`
   removes the attribution footer, with its line end stripped (a `\r` included, as the Windows line-end test of
   `tests/kit/test_session_flow.py` shows); a reason may follow on the lines after it.
2. Every other rule of a release stays: the same account, the same session, later than the take, and the build it
   names or every build when it names none. A comment whose first line is not a release frees nothing, even when a
   later line is one.
3. A `taken:` comment keeps today's whole-body reading.

## Consequences

A builder may say why it gives a brief back, and the brief is free at once for the slot the conductor assigned.
`session.py next`, `mine`, `plan` and every reader of `live_takes` see the release, since they all read takes through
`all_takes`. `session_plan.py` reads a release once more on its own, to date a session's last activity; that reading
is outside the brief's `Touches:` and is unchanged, so a reasoned release does not count there as activity.

## Residual

- 2026-11-11: the after-measure is the brief's `Measured:` command, which prints `[True]` for a reasoned and a bare
  release on this branch. Whether the next reasoned release in the queue frees the assigned slot at once is seen on the
  next such release, not measured here.

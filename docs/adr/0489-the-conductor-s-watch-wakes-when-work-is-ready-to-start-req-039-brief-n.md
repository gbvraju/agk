# ADR-0489: The conductor's watch wakes when work is ready to start

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: ADR-0402, ADR-0475, ADR-0482, brief #1125, brief #1151, plan #661
- Requirements: REQ-039

## Context

`conductor.py watch` ends on a new `Question:`, `Report:` or owner's answer, on a green label line, on a held review
(ADR-0482) or after about 5 minutes with `tick`. It never ends because `session.py plan` offers a brief that nobody has
started, so the conductor starts builders only when something else wakes it. On 2026-11-12 the red-branch brief #1150
opened at 22:56Z and had no `Started:` line until the co-owner started it at 23:05Z; #1095, offered from about 22:10Z,
was started by the co-owner at 22:19Z.

## Decision

1. With `builder_start = "assign"`, when a poll of `watch` finds no new line and no held review, `start_lines` reads the
   plan with `session_plan.build` (what `session.py plan` prints) and returns, for each row of its `assign` list whose
   brief has no comment starting `Started: cb` or `taken:` created in the last 2 hours, one line
   `START #<brief>[ build (<x>)] <kind>`; `watch` prints the lines and returns 0 the way it prints new lines. A row whose
   title is `The default branch is red` comes first, as `START #<brief>[ build (<x>)] red`.
2. The plan is read at most once per 60 seconds across watches: the time is kept in the file `agk/starts` of the
   checkout's git directory (beside the lease mark, never tracked), written before the reads. A plan that cannot be read
   returns no line. Without a git directory, or with `builder_start = "start"`, there is no read.
3. The same file keeps when each brief (and build) was last returned; one is returned again only after 10 minutes. A brief
   the plan no longer offers loses its mark.
4. The conductor's start rule (firing the builder task by kind and posting `Started: cb<brief> ...`) is unchanged and
   stays in its instructions; `.claude/agents/conductor.md` is not edited. No new setting or label.

Protected path classes changed: `scripts/agk/` (`conductor.py`), `tests/kit/` (`test_conductor_start_wake.py`) and
`agk.toml` (the `conductor.py` entry of `[[testing.map]]`).

## Consequences

A brief the plan offers wakes the conductor within about a minute of a quiet poll, red-branch work first, without a
person starting it. The watch makes at most one plan pass per minute, plus one comments read per offered brief, and
none while new lines or held reviews keep arriving.

## Residual

- 2026-11-12: a red-branch fix brief that is not itself titled `The default branch is red` is listed in plan order, not
  first; the plan does not expose its fix-brief mark (due 2027-01-31).

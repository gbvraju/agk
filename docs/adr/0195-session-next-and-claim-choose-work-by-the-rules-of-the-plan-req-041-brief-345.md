# ADR-0195: session next and claim choose work by the rules of the plan (REQ-041, brief 345)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0124, ADR-0125, ADR-0155, ADR-0189
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #345 (priority 2). ADR-0189 (brief #330) made `session.py plan` judge overlap by files and stopped claims of sessions that posted nothing for a day from holding a brief, but left `session.py next` on its older rules (Q-330-1): a folder prefix overlapped any path under it, a taken brief overlapped by the fixed parts of its `Touches:`, and every live take held. So the plan and `next` could disagree about the same brief. The field notes of 2026-10-30 on #345 add `session.py claim`: on #263 a take four days old (builder-f, build (c)) refused `claim --build c` only because a pull request of another build of the brief had just merged and kept every take of the brief live. The tests were written first.

## Decision

1. **One rule set (answer 1).** `next` uses the plan's functions instead of its own: the stale-claim reading (`gone_sessions` with `[flow] claim_stale_hours`, through `read_gone`), `settle_takes` for the briefs a take holds, and `running_conflict` (which uses `clash`, `file_conflict`, `covering` and `entries_of`) for the overlap with taken briefs and open builder pull requests. A brief whose only take is stale, or for a brief built in parts whose takes all belong to sessions that moved on, is free and is not running work. The take check of `next` and `claim` reads takes the same way (`holding`): a take of a gone session, or for a brief built in parts of a session that moved on, is no rival.
2. **The plan's reason (answer 1).** A skip prints the plan's words: `skip #6: waits for #5 (both touch a/x.py)`, `skip #5: waits for pull request #20 (it changes tests/kit/test_x.py)`, and `skip #5: taken by builder-f until 18:02 UTC` (or `while its pull request is open`). The plan's words and `next` use one function (`wait_text`).
3. **Nothing else in `next` changes (answer 2):** the capacity check comes first, the order is priority then number, `Depends-on`, the reserved numbers and the one take are as before; a freed brief takes its place in that order and its take says `retakes`.
4. **`claim` (the field note of 2026-10-30).** When a live take of another session exists, `claim` reads the open briefs and their comments and judges the gone sessions as the plan does; when the open briefs or any of their comments cannot be read, nobody is judged gone and an old take still holds, as before.
5. **Readings taken where the brief leaves a point open:** `session.py demand` keeps its own overlap count; the brief names `next` and `claim` only (Q-345-1). An added file of an open pull request now holds a brief only on its exact path in `next`, as in the plan (ADR-0189 decision 1); one test of `next` that relied on an added file under a folder now serves a modified file. Flow mode: fragment `changelog.d/next-plan-rules.md`; no version bump.

## Consequences

- `next` and `plan` give the same answer for the cases of #330's tests: two briefs with different files under one folder, a folder-only brief against a pull request changing a file under it, a stale claim, and a fresh claim with no pull request (`tests/kit/test_session_next_plan.py`).
- `next` reads the comments of the open issue labelled `agk-conductor` and of a session's pull requests only when some session would otherwise be stale, as the plan does; `claim` reads the open briefs only when another session's take is live.

## Residual

- 2026-10-30: `session.py demand` still counts ready briefs with the older overlap (Q-345-1); a later brief may give it the plan's rules (due 2026-12-31).

## Log

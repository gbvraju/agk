# ADR-0130: a blocked or waiting session tells the conductor, and its wait never goes silent (REQ-041, brief #210)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0125, ADR-0118
- Requirements: REQ-041

Protected classes: `.claude/`, `config/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Brief #210 (Advances REQ-041, Size S, assigned to `builder-c` on #204). Measured on 2026-10-25: a builder's `session.py watch --assign builder-b` printed nothing for more than 30 minutes because `watch_assign` read a
failed read as "no comments yet" and looped; a portal session's refused push was asked in its own chat and not as a `Question:` where the conductor reads; a builder stopped before an answer came because no wait existed yet
(fixed by #203). Each needed a person to carry a message. The numbers ADR-0130 and amendment 67 were reserved on #210 by the conductor. The tests were written first (`tests/kit/test_session_silent.py`; before the code 12
of its cases failed).

## Decision

1. **A wait ends with an error** (`scripts/agk/session.py`, `Reads`): `watch --pr`, `--merged` and `--assign` print one line `error: <what> cannot be read` and exit 4 when GitHub cannot be read for 5 polls in a row;
   `<what>` is the pull request, the comments of a pull request or the comments of the conductor issue, by number. A single failure is retried and a good read resets the count. The first read of the comments is part of
   the wait; `watch --assign` no longer starts from an unread baseline (it made an old `Assign:` line look new), and no longer treats a failed read as "no comments yet".
2. **A wait says what it waits for**: `watch --assign` prints `waiting on #<issue> since <id>` once when it starts (the id of the session's `Request:` comment, else the newest comment) and flushes it; the polls that do
   not end a wait write nothing.
3. **Session rules** (`config/session-rules.md`): rule 21, a session that is blocked for any reason posts `Question: Q-<id> <text>` on its pull request, or on its brief when it has none, then waits there, and never
   asks only in its own chat; an `error: ... cannot be read` is said on GitHub, or in the chat when GitHub is what it cannot reach. Rule 22, a session pushes only the branch its runtime gives it and opens its pull request
   from that branch. The conductor role file says it reads `Question:` comments on briefs as on pull requests.
4. Amendment 67 (`docs/runs/proposed-spec-amendments-67.md`) is applied to SPEC-0030 rules 2 and 6 and SPEC-0034 rules 11 and 12. The guide ("Running the loop") names the error end. A flow-mode fragment
   `changelog.d/req-041-silent-wait.md` records the change.

## Readings taken where the brief leaves a point open

Recorded as questions in the pull request, the most conservative reading each: "5 polls in a row" counts a poll as failed when the pull request, or its comments, or the conductor issue's comments cannot be read, whatever the
interval; the exit code 4 is new and `timeout` stays 3; the open case of answer 6 (what a session does when GitHub cannot be reached at all) is not built, because it is not posted on #210.

## Consequences

- A session whose wait cannot read GitHub is woken after five polls (five minutes at the default interval) with a line that says why, instead of waiting for hours.
- A blocked session leaves its question where the conductor reads; the conductor's `Question:` reading covers briefs with no pull request yet.

## Residual

- 2026-10-25: a wait cannot tell GitHub being unreachable from a revoked permission; both read as `cannot be read` (due 2026-12-31).
- 2026-10-25: rule 22 says a session pushes only the branch its runtime gives it; briefs and verdicts of this repository have named other branch names (`intake/`, `build/`), which the conductor reconciles (due 2026-12-31).
- 2026-10-25: answer 6 of the conductor's proposal (GitHub unreachable altogether) is not part of this build until it is posted on #210 (due 2026-12-31).

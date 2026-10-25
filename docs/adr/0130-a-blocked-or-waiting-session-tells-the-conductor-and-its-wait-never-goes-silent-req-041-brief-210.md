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
of its cases failed, then 10 more for answer 6).

## Decision

1. **A wait ends with an error** (`scripts/agk/session.py`, `Reads`): `watch --pr`, `--merged` and `--assign` print one line `error: <what> cannot be read` and exit 4 when GitHub cannot be read for 5 polls in a row;
   `<what>` is the pull request, the comments of a pull request or the comments of the conductor issue, by number. A single failure is retried and a good read resets the count. The first read of the comments is part of
   the wait; `watch --assign` no longer starts from an unread baseline (it made an old `Assign:` line look new), and no longer treats a failed read as "no comments yet".
2. **A wait says what it waits for**: `watch --assign` prints `waiting on #<issue> since <id>` once when it starts (the id of the session's `Request:` comment, else the newest comment) and flushes it; the polls that do
   not end a wait write nothing.
3. **Session rules** (`config/session-rules.md`): rule 21, a session that is blocked for any reason posts `Question: Q-<id> <text>` on its pull request, or on its brief when it has none, then waits there, and never
   asks only in its own chat; an `error: ... cannot be read` is said on GitHub, or in the chat when GitHub is what it cannot reach. Rule 22, a session pushes only the branch its runtime gives it and opens its pull request
   from that branch. The conductor role file says it reads `Question:` comments on briefs as on pull requests.
4. **When GitHub cannot be reached at all** (answer 6, posted on #210 and approved by the maintainer; part of this build): the five failed polls of answer 1 end with the one line
   `github-unreachable: <what> cannot be read; local head <sha> not pushed; next: push, then post the Report:/Question:` when `gh` says it could not connect (`session.py` keeps the last error text of `gh` and reads
   it for a network failure: could not resolve, dial tcp, connection refused or reset, i/o timeout, TLS handshake, timed out); any other failure (an error response, a 403, a 404) is GitHub answering and keeps the line
   `error: <what> cannot be read`. The head part says only what is true: `not pushed` (also with no upstream), `pushed` or `none` without a commit. A rate limit (`rate limit` or HTTP 429 in the error text) is not a
   failure: `gh()` reads the reset time from `GET rate_limit` (free of the limit), waits until it plus one second, and retries the call, at most five times for one call, and the wait goes on. Session rule 23 names the
   restart order (`push-check`, push the local commits, post the `Report:` or `Question:` owed, before anything else), that work stays local with its checkpoints, and that there is no second channel. A push is the
   session's own `git` command, so its five tries are the session's, by rule 23.
5. Amendment 67 (`docs/runs/proposed-spec-amendments-67.md`) is applied to SPEC-0030 rules 2 and 6 and SPEC-0034 rules 11 and 12. The guide ("Running the loop") names the error end. A flow-mode fragment
   `changelog.d/req-041-silent-wait.md` records the change.

## Readings taken where the brief leaves a point open

Recorded as questions in the pull request, the most conservative reading each: "5 polls in a row" counts a poll as failed when the pull request, or its comments, or the conductor issue's comments cannot be read, whatever the
interval; the exit code 4 is new and `timeout` stays 3; an outage is told from a refusal by the text of `gh` (the message of a network failure), because `gh` gives no status code for a failed connection; the reset time of a
rate limit is read from `GET rate_limit`, because `gh api` prints no response headers for an error.

## Consequences

- A session whose wait cannot read GitHub is woken after five polls (five minutes at the default interval) with a line that says why, instead of waiting for hours.
- A blocked session leaves its question where the conductor reads; the conductor's `Question:` reading covers briefs with no pull request yet.

## Residual

- 2026-10-25: a wait cannot tell GitHub being unreachable from a revoked permission; both read as `cannot be read` (due 2026-12-31).
- 2026-10-25: rule 22 says a session pushes only the branch its runtime gives it; briefs and verdicts of this repository have named other branch names (`intake/`, `build/`), which the conductor reconciles (due 2026-12-31).
- 2026-10-25: the classification of an outage reads the text of `gh`, which can change between versions (`(verify)`); a failure that matches none of the patterns reads as `error:` (due 2026-12-31).

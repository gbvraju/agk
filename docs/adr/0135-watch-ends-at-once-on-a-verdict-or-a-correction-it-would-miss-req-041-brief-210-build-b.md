# ADR-0135: `watch --pr` ends at once on a verdict or a correction it would miss (REQ-041, brief #210 build (b))

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0130, ADR-0118, ADR-0126
- Requirements: REQ-041

Protected classes: `config/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #210, follow-up item seen on #209: a builder's `watch --pr 209` printed nothing for more than 30 minutes, although a verdict naming its head was posted 1 minute 44 seconds after its `Report:`. `watch` ended only on
comments newer than the newest one it saw at start, so a verdict that landed between the push and the start of the watch, or a watch restarted later, was never seen. The conductor made it build (b) of the brief: at
start, `watch --pr` ends at once when the latest verdict by a listed author names the current head and no newer push has followed it, and the same for a `Correction:` it would otherwise miss; tests cover a verdict posted
before the watch starts and an older verdict on a previous head, which must not end it. ADR-0135 and amendment 71 were reserved on #210. The tests were written first (`tests/kit/test_session_missed.py`; before the code
10 of its cases failed).

## Decision

1. **At start** (`scripts/agk/session.py` `watch`, at its first poll): the floor is the id of the newest `Report:` comment by the pull request's author (0 without one), or `--since` when that is greater. The watch ends
   at once, printing the line it prints for the event, when (a) the latest verdict by a listed author (the pull request's own author dropped when two are listed) names a prefix of the current head and is newer than the
   floor, or else (b) a `Correction:` comment of a listed author, on the pull request or on the brief named by its `Brief: #n` line, is newer than the floor. The latest verdict decides: an earlier verdict that names
   the current head does not count when a later one names another. A verdict by an unlisted author, one that names a previous head and one before the floor never end it.
2. **`--since <comment id>`** (`watch --pr` only, a whole number): raises the floor. A session that has already acted on a verdict and only waits for CI or for the merge restarts the watch with the id that the line
   printed, so that the same verdict is not reported at each restart.
3. `config/session-rules.md` rule 24 and the guide ("Running the loop") say so. Amendment 71 (`docs/runs/proposed-spec-amendments-71.md`) is applied to SPEC-0030 rule 2 and SPEC-0032 rule 10. A flow-mode fragment
   `changelog.d/req-041-watch-missed.md` records the change. The tests of `test_session.py` that put an older verdict naming the current head before the start now name a previous head or put a `Report:` after it.

## Readings taken where the brief leaves a point open

Recorded as questions in the pull request, the most conservative reading each: "no newer push has followed it" is read as "newer than the last `Report:` of the pull request's author", because GitHub reports no push time for a
head and a verdict that names the current head is by construction not followed by a push; `--since` is added because without it a session that restarts the watch while it waits for CI after a fix-list verdict would be
woken at once by the same verdict at every restart; a `Report:` of another account does not set the floor (the account is the pull request's author, shared with the conductor until lane F).

## Consequences

- A verdict posted between a session's push and its watch is seen, and so is a restarted watch after a verdict nobody acted on.
- A session that waits after a verdict must pass `--since`; without it the watch ends at once with the same line (never silently).

## Residual

- 2026-10-25: the floor is the last `Report:` of the pull request's author; a session that pushes without a `Report:` (against the session rules) keeps an older floor, and a verdict newer than it ends the watch at once (due 2026-12-31).
- 2026-10-25: the author of the pull request and the conductor share one account until lane F, so a `Report:` of the conductor would also be a floor (due 2026-12-31).

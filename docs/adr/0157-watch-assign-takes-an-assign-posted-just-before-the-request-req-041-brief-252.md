# ADR-0157: `watch --assign` takes an `Assign:` posted just before the `Request:` (REQ-041, brief 252)

- Status: Accepted
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0125, ADR-0130
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`, `.claude/`, `config/`

## Context

Brief #252 (priority 2): the conductor often posts a builder's next `Assign:` as soon as its pull request merges, before the builder posts its `Request:`. `session.py watch --assign <session>` took only an `Assign:` posted after that `Request:`, so the conductor posted each assignment twice to be sure it was seen (#204: #236, #238, #242, #247, #251). The tests were written first and failed on the unchanged tree.

## Decision

1. **The window.** `watch --assign <session>` also takes the newest `Assign: <session> ...` by a listed verdict author posted after the session's previous `Request:` (any time before, for a session's first `Request:`) and before its current one. It prints it on its first poll and ends, as it does for a line posted after the `Request:`. An `Assign:` posted after the current `Request:` answers that `Request:` and wins over an early one.
2. **Never taken twice.** An early `Assign:`, of a brief or `none`, is spent when the session has a `taken: <session> ...` comment on any brief newer than the `Assign:` (comment ids, which GitHub numbers in order across issues; read once from the repository's issue comments since the line was posted), because a session takes what it was assigned; then the wait goes on for a new line. This also spends a stale `Assign: <session> none` left by an earlier session of the same name (session names are reused), which would otherwise end the next session at once (the verdict on 2691a48). An `Assign:` older than the previous `Request:` is outside the window. Only the newest early line counts: an older one is never taken in its place.
3. **`Assign: <session> none`** posted early ends the wait the same way, under the same test of answer 2.
4. **Takes that cannot be read** are retried, with their own count of five polls, and the line is never taken unchecked; the wait then ends with `error: the comments of the briefs cannot be read` (exit 4).
5. **The rules.** The conductor role (`.claude/agents/conductor.md`) says it may assign before the `Request:` and need not repeat the line; session rule 18 (`config/session-rules.md`) says the wait takes it. No spec rule changes, so no amendment. Flow mode: fragment `changelog.d/assign-before-request.md`; no version bump.
6. **A test changed by the brief.** The test that an `Assign:` before the `Request:` is ignored now puts a previous `Request:` between them (answer 2: an `Assign:` older than the previous `Request:` is ignored); without it the same line is now an early assignment by answer 1.

## Consequences

- The conductor posts each assignment once, whenever it is ready, and no assignment is missed.
- A wait reads the issue comments posted since an early line, once, when there is one.

## Residual

- 2026-10-26: the `taken:` check trusts the session id in the comment, as `claim` does; one shared account for all sessions means the check cannot tell who posted it (a residual of SPEC-0032 rule 6), due 2026-12-31.

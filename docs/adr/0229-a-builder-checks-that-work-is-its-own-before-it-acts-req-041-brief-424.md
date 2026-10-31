# ADR-0229: a builder checks that a pull request or brief is its own before it acts on it (REQ-041, brief 424)

- Status: Proposed
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0187, ADR-0195
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `config/`, `tests/kit/`

## Context

Brief #424, from the #286 field note of 2026-10-27 (wrong window): a person pasted an instruction meant for one builder
into another builder's tab; that builder edited the other's pull request description and started a second watch on it,
so two builders reacted to one pull request. The takes (`taken:` comments on a brief) already say which session holds
which work, but nothing makes a builder read them before it acts. `session.py` (`scripts/agk/`), the session rules
(`config/`) and their tests (`tests/kit/`) are protected path classes, so this ADR names them. The tests were written
first (`tests/kit/test_session_flow.py`, the `mine` tests: 7 failed, 6 passed at the first checkpoint; the 6 passing are
the usage refusals, which an unknown command also gives).

## Decision

1. **`session.py mine --session ID (--pr N | --brief N)` (answer 1).** It only reads GitHub (GET). For `--brief N` it reads
   the brief's comments and every pull request, and judges the takes as `next` and `claim` do (`live_takes`: a take is
   live until a `released:` of its session by the same account, and for `claim_hours` or while an open pull request names
   the brief, or a merged one for `claim_hours` after its merge). For `--pr N` it reads the pull request and judges the
   brief that its `Brief: #n` line names. It prints `mine` and exits 0 when one live take is the session's, for any build
   of the brief; otherwise `not mine: #<brief> belongs to <session>` (the oldest live take of another session) or
   `not mine: #<brief> has no live take`, and exits 1. A pull request without a `Brief:` line prints
   `not mine: #<pr> names no brief` and exits 1 (Q-424-1). A read that fails prints `FAIL session: rule 5: ...` and exits
   2, never `mine`. It takes exactly one of `--pr` and `--brief`; anything else prints the usage and exits 2.
2. **Session rule 35 (answer 2).** Before a builder acts on a pull request or a brief that a message names, it runs `mine`;
   on `not mine:` it replies with that line and does nothing else.
3. **Tests (answer 3).** The session's own take; another session's take; a released take (and an expired one); a pull
   request with no `Brief:` line; a brief built in parts where the session holds one build; a pull request judged by its
   brief; an unreadable read; the usage refusals.

## Consequences

- A message pasted into the wrong tab makes the builder say `not mine: ...` instead of editing another builder's work.
- `mine` posts nothing and changes no take; it is not one of the commands that a pause refuses, since it reads only.

## Residual

- Q-424-1 (2026-10-31): the brief gives no output for a pull request without a `Brief:` line; no take can make it the
  session's, so the conservative reading is `not mine`, with its own reason `names no brief`, and exit 1.
- Q-424-2 (2026-10-31): for `--pr`, `#<n>` in the `not mine` line is read as the brief's number, the issue that holds the
  take; the pull request's number is the one the message named, so the builder already has it.

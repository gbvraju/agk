# ADR-0206: a builder sees its messages while it waits on its pull request and when its work is done (REQ-040, brief 368)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0187
- Requirements: REQ-040

Protected classes: `scripts/agk/`, `config/`, `tests/kit/`

## Context

Brief #368 (#286 part 2). ADR-0187 (brief #327) added `session.py tell` and `inbox`, but only `watch --assign` prints new
`Tell:` lines. A builder spends most of its time in `watch --pr N`, which knows no session and never reads the
`agk-conductor` issue, and `after` printed nothing from the inbox, so a `Tell:` such as `#52 merged, rebase` sent while a
builder waits on its pull request was read only when someone told the builder to look. The tests were written first
(7 failed, 31 passed in `tests/kit/test_session_tell.py` at the first checkpoint; the four tests of the verdict on
e90f60b failed 4, passed 37 at their checkpoint).

## Decision

1. **`watch --pr N --session ID` (answer 1).** With `--session` the watch reads the comments of the one open
   `agk-conductor` issue at its start (the baseline) and on every poll, and ends with the one line `tell <message>` on a
   comment newer than the baseline whose first line is `Tell: <ID> <message>` by a listed verdict author (the same
   reading as `inbox` and `watch --assign`). A verdict, a merge, a close, a conflict, a correction and a label change
   of the same poll keep their place before it. The conductor issue has its own count of unread polls: five in a row end
   the watch with `error: the comments of #<n> cannot be read` (exit 4, session rule 21). A failed listing of the
   `agk-conductor` issues is retried the same way, and the fifth in a row ends the watch with
   `error: the open issues labelled agk-conductor cannot be read` (exit 4). Without exactly one such issue (a project
   with `assign = "next"` need not have one) the watch prints `messages: not read (no open issue labelled agk-conductor)`
   or `(more than one open issue ...)` and goes on watching the pull request as it does without `--session` (the
   verdict on e90f60b, item 1). `--session` is taken by `watch --pr` only. Without it the watch
   makes exactly the calls it made before and never reads the conductor issue.
2. **`after --session ID` (answer 2).** `after` first prints the unread `Tell:` lines as `inbox` does, with the same mark
   in the git directory, so a message is printed once by either command; then it prints what it printed before. An
   inbox that cannot be read is said in one line (`tell: ...`) and is never shown as an empty one, and `after` goes on.
3. **Session rules 10 and 32 (answer 3)** name `--session` in the `watch --pr` command and say that a builder reads a
   `tell` line as information and starts `watch` again.
4. **Tests (answer 4)** in `tests/kit/test_session_tell.py`; the existing test of `after` in conductor mode in
   `tests/kit/test_session_assign.py` now serves an empty conductor issue, since `after` reads it first.

## Consequences

- A `Tell:` sent while a builder waits on its pull request wakes it, with no person copying text between tabs.
- A `Tell:` posted between the end of one watch and the start of the next is not printed by the next watch, which counts
  from its own start; `after` and `inbox` still print it once.

## Residual

- `docs/guides/getting-started.md` step 4 still shows `watch --pr <number>` without `--session` (Q-368-1, 2026-10-30).

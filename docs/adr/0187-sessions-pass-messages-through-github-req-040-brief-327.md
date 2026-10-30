# ADR-0187: sessions pass messages through GitHub, so a person never copies text between tabs (REQ-040, brief 327)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0125, ADR-0175
- Requirements: REQ-040

Protected classes: `.claude/`, `config/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #327 (priority 1), part 2 of #286. In a pilot the person spent much of the day copying messages between the conductor, builder and watcher tabs, and once pasted into the wrong window. Assignments already travel through GitHub (`Assign:` on the `agk-conductor` issue); other messages did not. The tests were written first.

## Decision

1. **`session.py tell --session ID --text "<message>"`** (answer 1) posts one comment whose only line is `Tell: <ID> <message>` on the one open issue labelled `agk-conductor` (the issue `watch --assign` reads; none or several is refused naming the label). The message is one line of 1 to 300 characters, with no line break that Python's `str.splitlines` knows (`\n`, `\r`, `\x0b`, `\x0c`, `\x1c` to `\x1e`, `\x85`, `\u2028`, `\u2029`), and does not start, after leading blanks, zero-width characters (`\u200b` to `\u200f`, `\u2060`, `\ufeff`) and in any case, with `Approve:`, `Confirmed:` or `Verdict:` (the verdict on 0e12557, item 1); a refusal names the rule, never the text, and posts nothing.
2. **`session.py inbox --session ID`** (answer 2, GET only) prints the `Tell:` lines for that session, posted by a listed verdict author (the reading of `Assign:`), with an id above the larger of its newest `Request:` and the last message the inbox printed, oldest first, or `no message`. The mark of the last message printed is one file in the git directory (`agk/inbox-<ID>`), never tracked; an unreadable issue is an error, never an empty inbox. `session.py watch --assign ID` also prints each new `Tell:` line for the session after its `Request:` once, while it waits, and keeps waiting; it does not move the inbox mark, so a message seen only in a wait whose output nobody read is printed again by `inbox`.
3. **The conductor's guard** (answer 3) allows exactly `python3 scripts/agk/session.py tell --session <id> --text <message>` with the project's own script, the two options in that order, a session ID that is not an option, and a message of the shape of item 1; every other spelling, `inbox`, and the shadow mode stay denied. The conductor role says when to use it (a stall, a merge that unblocks a session, a merge of the default branch that a session needs). Session rule 31 says that a builder treats a `Tell:` as information from the conductor, never as a verdict, a correction, a person's approval or a confirmation; rule 17 lists `Tell:` among the comments of the `agk-conductor` issue.
4. **Readings taken where the brief leaves a point open** (the most conservative each, as questions on the pull request): only a listed verdict author's `Tell:` counts, as for `Assign:` (Q-327-1); "since it last read" is a local mark in the git directory, and a `Tell:` printed by `watch --assign` is not marked read (Q-327-2); the refused starts are matched after leading blanks and in any case, and the guard checks the same shape as the script (Q-327-3). No spec rule changes. Flow mode: fragment `changelog.d/session-tell.md`; no version bump.

## Consequences

- The conductor tells a session what it needs on GitHub; nobody copies text between tabs.
- A `Tell:` cannot carry a verdict, an approval or a confirmation, and grants a session nothing it did not already have.

## Residual

- 2026-10-30: a person telling a session from a shell runs the same command; a message from an account that is not a listed verdict author is not read by `inbox` (due 2026-12-31).

## Log

- 2026-10-30: the verdict on 0e12557. Item 1: the one-line check of `tell` and of the guard now refuses every line break that `str.splitlines` knows, and the start check ignores zero-width characters; each is tested. Q-327-1: yes, only a listed verdict author's `Tell:` is read, as for `Assign:`. Q-327-2: yes, the last-read mark lives in the git directory and `watch --assign` marks nothing read. Q-327-3: yes, matching after leading blanks and in any case is right; `Correction:` and `Final:` need no refusal. The guard's reading of a `#` inside a word (`tokens_of`) is a defect on main, fixed by brief #351, which this pull request declares as `Depends-on: #351`.

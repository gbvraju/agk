# ADR-0222: the review queue lists unanswered requests and questions on briefs, and the pass answers them (REQ-037, brief 408)

- Status: Accepted
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0198
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`

## Context

Brief #408 (from the #286 field notes of 2026-10-27 and 2026-10-29): nine builders ran `session.py after`, posted
`Request:` on the `agk-conductor` issue and waited up to 64 hours for an `Assign:` line, because the review pass reads
pull requests only. Session rule 21 also sends a builder with no pull request to ask on its brief, which `review-queue`
never read. ADR-0198 (brief #350) closed the same gap for drafts. The command, the skill and their tests are protected
path classes, so this ADR names them. The tests were written first (`tests/kit/test_session_review.py`: 13 failed at the
first checkpoint of the pull request).

## Decision

1. **Requests (answer 1).** After the pull requests, `session.py review-queue` lists each comment on the one open
   `agk-conductor` issue whose first line is `Request: <session> ...` and that no later comment answers with a first line
   `Assign: <session> ...` (the form `watch --assign` reads) by a listed verdict author, as
   `request <session> (comment <id>) waiting <minutes>m`, the minutes counted from its creation. With no open
   `agk-conductor` issue nothing is listed (a project with `assign = "next"`); with two or more the command fails naming
   the label, as `watch --assign` does.
2. **Questions on briefs (answer 1).** It lists each open `agk-brief` issue that has a live `taken:` (as `next` and the
   plan read a take, `claim_hours` included), that no open pull request names with `Brief: #<brief>`, and that has a
   `Question:` comment created or edited after the brief's last comment by a listed verdict author, as
   `#<brief> question on a brief`. A session's own lines (`Question:`, `taken:`, `released:`, `taken over:`) are never
   that last comment, since a session may post as a listed author (Q-408-1). A brief with an open pull request (a draft
   included) is left to that pull request's rules.
3. **The fingerprint (answer 2).** `--fingerprint` adds, for each listed request, its session, id and time, and for each
   listed question, its brief, id and time, never the minutes waited, so a new or edited request or question wakes the
   loop and the passing of time does not.
4. **The pass (answer 3).** `/agk:review-pass` answers a request with one comment `Assign: <session> #<brief>` (with
   `build (<x>)` when built in parts) when the start list of `session.py plan --json` names that session, else
   `Assign: <session> none` (Q-408-3), and a question on a brief with one comment on that brief that answers it. The last
   lines gain one line per answer. Nothing else in the pass changes.
5. **Read only.** The command still makes GET calls only; a list or comment page that cannot be read fails it, never
   reading as empty. The pull requests of every state are read only when a brief has a waiting question, to judge its take.

## Consequences

- A builder waiting on an assignment or on an answer on its brief is in the next pass's queue, with how long it has waited.
- A pass reads one more issue and the comments of each open brief with no open pull request.
- An old `Request:` that nobody answered is listed until a person or the conductor answers it, even when its session has
  ended; `Assign: <session> none` clears it.

## Residual

- Q-408-1 (2026-10-31): the sessions of this repository post as the one listed verdict author, so "the brief's last comment
  by a listed author" would be the question itself. The conservative reading: a comment by a listed author whose first line
  is a session's own (`Question:`, `taken:`, `released:`, `taken over:`) is not an answer; any other one is.
- Q-408-2 (2026-10-31): the brief says "the one open `agk-conductor` issue" and does not say what two or none mean. As built:
  none lists no request, two or more fail the command naming the label, as `watch --assign` does.
- Q-408-3 (2026-10-31): the plan names fresh sessions (`builder-a`, `builder-b`, ...), so a waiting session it does not name
  is answered `Assign: <session> none`, as the brief says, which ends that session. Whether the pass may instead give it one
  of the plan's starts is for the conductor.
- Q-408-4 (2026-10-31): a take ends after `claim_hours` without a pull request, so a question on a brief stops being listed
  once the take expires; the brief asks for a live `taken:`. A question that waits longer is a later brief if it bites.
- Q-408-5 (2026-10-31): an `Assign:` posted before the `Request:` (brief #252's early answer) does not answer it here, since
  the brief says "after it"; the conductor then answers it again.

# ADR-0553: The review queue reads only the briefs in play

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0548, ADR-0529, brief #1309, brief #1251, brief #408, plan #661
- Requirements: REQ-050

## Context

Brief #1309 found, in a project with about 650 open `agk-brief` issues, that `session.py review-queue` (every
conductor pass, `--fingerprint` and `--all` alike) took about three minutes: `brief_questions` reads every page of
the comments of each open brief that no open pull request names, to find a live take with an unanswered
`Question:`, so about 650 calls a pass, although almost none of those briefs has a comment or a take. CI, local and
personal mode run the same script.

## Decision

1. From the one listing of the open briefs it already makes, `brief_questions` reads the comments of a brief only
   when the brief can hold a live take: it carries the take label `agk:taken` (added by `claim` since brief #1251),
   or its listing shows `comments` above 0 and an `updated_at` other than the one kept from the last pass. A brief
   whose listing shows `comments` 0 is never read, under the label or not. A listing that shows no `comments` count
   is read as before.
2. The kept times are a note beside the read cache of ADR-0548 (`quiet_briefs`, in the repository's cache file):
   for each brief without the label that a pass read and found with no unanswered `Question:`, its `updated_at`. A
   brief with a question is never kept, so it is read on every pass, since its take can lapse or stay live by the
   clock and by merged pull requests. The note is written only when a pass ends without an error, carries the
   verdict authors it was made for and is ignored when they differ (what answers a question changed). With the
   cache off (`AGK_READ_CACHE=off`) or unwritable, nothing is kept and every brief with comments is read.
3. A brief taken before the label existed is caught by rule 1's count and time: it is read once, and again on every
   pass while it holds a question. The lines and the fingerprint are those of a read of every brief, for the same
   GitHub state; a listing or a comment read that fails is an error (exit 2), never an empty queue, as before.

## Consequences

In the recorded double, a pass over 650 open briefs of which 3 are in play makes at most 6 calls beyond its three
listings, cold or warm, for `--fingerprint` and `--all`, and its fingerprint equals that of a read of every brief.
Protected path classes changed: `scripts/agk/` (`session.py`) and `tests/kit/` (`test_session_review.py`).

## Residual

- 2026-11-14 (verify): an issue's `updated_at` changes when a comment is added to it, which rule 1 relies on. Whether
  an edit of an existing comment changes it was not confirmed; an edited `Question:` on a brief without the label is
  then seen at the brief's next new comment or label change. A brief taken since brief #1251 carries the label and is
  read on every pass, so this touches only a take whose label could not be added.

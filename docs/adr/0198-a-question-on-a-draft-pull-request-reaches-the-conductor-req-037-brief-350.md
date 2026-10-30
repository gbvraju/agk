# ADR-0198: a question on a draft pull request reaches the conductor (REQ-037, brief 350)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0173, ADR-0175
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`

## Context

Brief #350 (priority 1): on 30 Oct 2026 two builders asked `Question:` comments on their draft pull requests (#342 and #344)
and waited about an hour. `session.py review-queue` (brief 306, ADR-0173) skipped every draft without reading its comments,
so no review pass listed them, and a person had to point them out. A question is the one thing on a draft that needs the
conductor.

## Decision

1. **A draft with a new question is listed (answer 1).** `review-queue` reads the comments of a draft and lists it, with the
   one reason `question on a draft`, when a `Question:` comment was created or edited after the last verdict by a listed
   author (or there is no such verdict). The rule against two verdicts on one head and the skip while checks run do not apply
   to it; the draft's checks are not read at all, because answering a question needs none.
2. **Every other draft stays skipped (answer 2).** A draft with an answered question, or with only a `Report:`, `Progress:`,
   `Correction:` or `Maintainer answer:`, is skipped with `draft` as before. `--fingerprint` now includes a draft's comment
   times (before, a draft contributed only its head, label and draft flag), so a new or edited question changes it and wakes
   the loop (Q-350-2). A draft whose comments cannot be read fails the command, as for any other pull request, and is never
   read as skipped.
3. **The pass answers without reviewing (answer 3).** `skills/review-pass/SKILL.md` adds the rule and says that a
   `question on a draft` is answered in a verdict on the draft's head whose numbered items are the answers, without a review
   of the draft's code.
4. **Tests first (answer 4).** `tests/kit/test_session_review.py` gains: a draft with a question (with no verdict, after a
   verdict on its head, and edited after the verdict) is listed; a draft with an answered question, or with only another kind of
   comment, is skipped; a verdict by an unlisted author answers nothing; the fingerprint changes on a new and on an edited
   question; an unreadable draft comment list fails. The existing test that a draft's comments are not read becomes a test that
   its checks are not read, since answer 2 needs its comments.

## Consequences

A builder blocked on a question while its pull request is still a draft is answered within one pass. A pass reads one more
GitHub list per open draft. A verdict that answers a draft's question names the draft's head; if the builder marks the pull
request ready on that same head, the rule against two verdicts on one head skips it until a new comment or push (Q-350-1).

## Residual

- 2026-10-30: Q-350-1, whether a pull request marked ready on the head of a verdict that only answered a draft's question
  should be reviewed again, is open.

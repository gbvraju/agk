# ADR-0413: A slot resumes its pull request when the question it stopped on is answered (REQ-040, REQ-041)

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: SPEC-0034, brief #961, plan #661, pull request #949, brief #459
- Requirements: REQ-040, REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

On 10 Nov pull request #949 posted `Report: d1e41cb escalate` with Q-459-1 and Q-459-2. The conductor
answered `Answer: Q-459-2` twenty minutes later, yet slot s1, which owns #949, ran and ended idle,
because `session.follow_up_owed` returned only `conflict` or `fix list`; a person restarted the build
by hand. Brief #961 asks that an answered question be a follow-up.

## Decision

`session.follow_up_owed` returns `answer`, after `conflict` and `fix list`, when the pull request's
author stopped on a question and it has been answered since. The author stopped when the newest
`Report:` of the author has `escalate` or `blocked` in its first line, or the newest comment of the
author starts `Question:`; the questions are the `Q-<n>-<x>` ids in that comment. It is answered by a
later comment of a listed verdict author or a spec approver whose first line is `Answer: Q-<n>-<x>`
or `Maintainer answer: Q-<n>-<x>` naming one of those ids, or starts `Correction:` and names one of
them anywhere in its body. A `Report:` by the author newer than the answer spends it. `slot_next`
prints `follow-up pr #<n> answer` in the place of the fix-list follow-up. The tests are in
`tests/kit/test_builder_slots.py`, marked `REQ-041`; the newest `Report:` or `Question:` of the author decides a `Question:` stop, since the answerer may post under the same login.

## Consequences

An escalated build continues on the slot's next run once the conductor answers, with no person
restarting it. An answer that names no question the builder stopped on, or comes from an unlisted
author, is not a follow-up.

## Residual

- 2026-11-10: a stop with no `Q-` id in its text can be answered only by a person's restart; Q-961-1.

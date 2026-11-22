# ADR-0715: The steward counts an override only from the owner, once per answer (REQ-066)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0546, ADR-0560, SPEC-0059, brief #1716, brief #1289, plan #661
- Requirements: REQ-066

Protected classes this pull request changes: `scripts/agk/` (`steward_daily.py`) and `tests/kit/`
(`test_steward_daily.py`). `kit/hashes.json` is not edited by hand.

## Context

SPEC-0059 rule 13 counts as an override "an owner's `Maintainer answer:` or `Correction:` that changes a steward
`Answer:`". `steward_daily.overrides` matched every `Correction:`, whoever posted it, and broke per comment, not per
answer, and `post_daily` read its recorded entries once before its loop. On 2026-11-20 one steward answer drew a
conductor `Correction:` that upheld it, the owner's answer and a conductor `Correction:` restating that answer: three
`Override:` entries for one answer, and a share of 4/7 where the owner overrode 2. The owner and every AGK session
post as one login, so the last `Who:` line (brief #1289, ADR-0546) is the only mark of the role: the owner's own
comments carry none, a relayed owner decision ends `Who: ProductOwner` (SPEC-0059 rule 5), a role's ends `Who: AGK …`.

## Decision

1. A comment is an override only when it is a `Maintainer answer:` that differs from the steward's answer, or a
   `Correction:` naming its Q id, and its last `Who:` line (the runtime's footer dropped) is absent or is
   `Who: ProductOwner`. A comment whose last `Who:` line names another role is never one, whether it upholds or
   reverses the answer (Q-1716-2, the conservative reading of "only from the owner").
2. Comments are read oldest first, and each steward answer yields at most one override, the earliest that
   qualifies. A `Maintainer answer:` is matched to the newest steward answer of its Q id before it.
3. `post_daily` adds each Q id it posts to the recorded set before the next, and the recorded set also reads the
   `Override:` entries among the comments it already read with `since=` (no new call), so an entry on a memory issue
   that rolled over is not posted again.
4. No setting changes the rule: `review_mode`, `execution`, `pr_mode`, `[steward] auto_file`, `[kit] layout` and
   `AGK_STEWARD_CACHE` are not read by these functions; in personal mode no comment is read, the share stays
   `unknown` and no entry is posted. No new `agk.toml` key.

## Consequences

The override share and its class warning count only the owner's changes, once per answer, so the figure stays
comparable across releases and roll-overs. The four entries already posted on the memory issue are not edited
(Q-1716-1): the steward may record the true share, 2/7 for 2026-11-20, as a `Lesson:`.

## Residual

None (2026-11-22).

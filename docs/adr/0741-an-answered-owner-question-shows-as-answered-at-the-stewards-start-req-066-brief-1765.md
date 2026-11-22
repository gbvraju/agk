# ADR-0741: An answered owner question shows as answered at the steward's start (REQ-066)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0557, ADR-0726, SPEC-0059, brief #1765, plan #661
- Requirements: REQ-066

Protected classes this pull request changes: `scripts/agk/` (`steward.py`) and `tests/kit/` (`test_steward_memory.py`).
`kit/hashes.json` is not edited by hand.

## Context

The steward test report of 2026-11-22 (problem 4): in the sample project the memory held `Owner question: Q-3-1 ...`
and after it `Decision: Q-3-1: yes on #3 at ...`, and the next `steward.py start` listed `Q-3-1` beside the open
`Q-3-5` and `Q-3-6` with no mark that it was done. `summary` printed the newest three entries of each kind with no look
at decisions; `open_questions` already found the open ones but only the roll-over used it.

## Decision

1. In the start's summary the `Owner question` kind lists only the open questions, by `open_questions` over the
   memory's comments, newest first, at most three, then `Owner question: <n> more open` when there are more.
2. One line `Owner question: <k> answered` follows when any question has a `Decision:` or `Maintainer answer:` naming
   its Q id. `open_questions` reads `Maintainer answer:` too, so the roll-over and `steward_owner.py`'s
   `memory_questions` count a relayed owner answer the same way.
3. A `not yet` decision counts as answered for this summary; asking again is a new ask. Every other kind prints as
   before, `refresh` is unchanged, and no setting is read; personal mode summarises the sidecar's memory file the
   same way.

## Consequences

A returning steward sees only what is still open and never asks the owner the same question twice.

## Residual

None (2026-11-22).

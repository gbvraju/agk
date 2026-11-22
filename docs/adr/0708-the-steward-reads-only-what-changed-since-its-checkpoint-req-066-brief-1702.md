# ADR-0708: The steward reads only what changed since its checkpoint (REQ-066)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0557, SPEC-0059, brief #1702, plan #661
- Requirements: REQ-066

Protected classes this pull request changes: `scripts/agk/` (`steward.py`), `.claude/` (`agents/steward.md`) and
`tests/kit/` (`test_steward_memory.py`, `test_steward_agent.py`). `kit/hashes.json` is not edited by hand.

## Context

ADR-0557 gives the steward one memory read, at `start`, with `since=` from a cache in the clone's git folder. Nothing
reads the memory again later in a pass, and nothing reads pull request state, so a check before a list is a set of
hand reads of whole comment pages. On 2026-11-22 a morning list asked for a decision the owner had already posted and
for lines of a pull request that had already merged (brief #1702).

## Decision

1. `start` keeps a checkpoint in the cache, beside the comments: the newest memory comment's `updated_at` and the
   start's UTC time. In personal mode it keeps the number of sidecar entries and the time. Nothing new is posted and
   no tracked file holds it.
2. `steward.py refresh --session ID` posts nothing and makes three GET calls: the memory comments with
   `since=<checkpoint>`, `pulls?state=open` and one page of `pulls?state=closed&sort=updated&direction=desc`. It prints
   one line per new or edited memory comment (`<id> [edited] <first word> <first 120 characters>`, a `Decision:` or
   `Maintainer answer:` first), one line `#<n> <head12> <labels>` per open pull request whose head or labels changed,
   one line `#<n> merged|closed <UTC time>` per pull request closed since the checkpoint, `more closed since <time>:
   not listed` when the page is full, and `refresh: nothing new since <time>` when nothing changed. It then moves the
   checkpoint to now and stores the open pull requests' heads and labels, so the next refresh compares against them;
   the first refresh after a start, which has none stored, takes an open pull request updated after the checkpoint as
   changed.
3. Without a checkpoint it is refused naming `AGK_STEWARD_CACHE` (exit 2); `--since <UTC time>` stands in for it. A
   failed call exits 4 and leaves the checkpoint where it was. When the memory issue holds 500 comments or more, so
   that another start may have rolled it over, `refresh` makes one more call, the open listing, and reads a newer issue
   from its first comment.
4. In personal mode `refresh` reads the sidecar entries after the checkpoint and prints `pull requests: not read in
   personal mode`, with no call. `execution`, `review_mode`, `pr_mode` and `AGK_STEWARD_START` do not change it; no
   `agk.toml` key is added.
5. The role file runs `refresh` before a list or a summary and never reads the memory issue or the pull requests in
   full for it. `end` stays a marker (Q-1702-1).

## Consequences

A list is current at the cost of three calls, whatever the size of the memory or of the pull request queue.

## Residual

None.

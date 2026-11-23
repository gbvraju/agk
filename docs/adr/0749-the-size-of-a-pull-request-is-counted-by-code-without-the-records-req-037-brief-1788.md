# ADR-0749: The size of a pull request is counted by code, without the records its brief requires (REQ-037)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1788, ADR-0583, plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `.claude/`, `tests/kit/`

## Context

ADR-0583's ruling 1 accepts a pull request whose changed lines, tests excluded, are at most three times its brief's
size guide (300 without one) and whose verdict names no finding. No script applied it: `rules.py size_ruling` was
called only by its tests, and the conductor counted by hand. On #1762 (brief #1757, a guide of about 100) the count
was 368 with the brief's own ADR, amendment and changelog fragment in it; its code and guides were 277, under the
ruling, and the change waited about 6 hours 40 minutes for an owner question. Every brief that changes a protected
path requires an ADR, so every such change carries record lines its guide does not plan for. The owner's word
(2026-11-23, the steward chat, quoted as data): "Yes, brief the size count fix."

## Decision

1. The count of ADR-0583's ruling 1 is the additions plus deletions of each changed file of the pull request, read
   from every page of its files, leaving out the records a brief requires: `tests/**`, `docs/adr/*.md`,
   `docs/runs/proposed-spec-amendments-*.md` and `changelog.d/*`. Everything else counts; a file with no line counts
   0. `rules.py` states it as `size_count`, the guide as `size_guide` (the `Plan:` line's `about <n> changed lines`),
   and `rules.py size --pr N` (GET only) prints the one size line and `records: <n> lines not counted`.
2. A finding for the ruling is a numbered item of the newest verdict that does not ask only for a merge of main, a
   re-prove or an evidence record (an item tagged `config/session-rules.md 30` alone is one); a rejected verdict is
   one finding (`Q-F4-1`, the conservative reading).
3. `conductor.full_problem`, run by `check-verdict --pr N` and the guard, refuses a verdict whose `Size:` lens line
   states another count, or says `accepted by standing ruling` when the ruling does not accept, and refuses an
   `Owner needed:` that asks about size when the ruling accepts.
4. The limit of ADR-0583 (three times the guide, 300 without one, no finding) is unchanged and ADR-0583 is not
   edited. Its ruling is withdrawn, for `rules.py size`, when ADR-0583's file is not Accepted or an Accepted ADR
   carries the line `- Withdraws: ADR-0583`; then every size over the guide is asked. More than 2999 files is
   `unknown` and asked, never accepted. In personal mode `rules.py size` prints `not run: personal mode`.

## Consequences

The conductor states the size the same way every time, and a change within the ruling is no longer parked for an
owner question about records its own brief required.

## Residual

- 2026-11-23: the guard reads only `Verdict:`, `Final:` and `Correction:` lines before a post, so an `Owner needed:`
  size ask is refused by `check-verdict --pr N`, which the conductor's role file names, not yet by the guard itself
  (`.claude/hooks/conductor_guard.py` was not in the brief's `Touches:`). A later brief may add it.

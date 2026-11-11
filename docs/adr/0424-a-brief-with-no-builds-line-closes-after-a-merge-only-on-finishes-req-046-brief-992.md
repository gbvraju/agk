# ADR-0424: A brief with no Builds: line closes after a merge only on Finishes (REQ-046)

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: ADR-0411, ADR-0273, SPEC-0039, brief #992, brief #959, brief #846, plan #661
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

ADR-0411 closes the brief of a merged body's `Brief: #N` when every build of its `Builds:` line
is named by a merged pull request's title, "or that names no builds". Session rule 28 says only
the last pull request of a brief carries `Finishes: #N` and `Closes #N`; an earlier build's
pull request names the brief with `Brief: #N` alone and does not close it. Brief #846 named its
two builds in a sentence, not in a `Builds:` line, so `session_plan.builds_of` returned `[]`
and the merge of #965, build (a), whose body had no `Finishes:` line, closed brief #846 on
2026-11-10 at 12:30:22 UTC with build (b) still to run.

## Decision

This changes one clause of ADR-0411's decision; the rest of ADR-0411 stands.

- A brief that names no builds (no `Builds:` line) is closed after a merge only when the merged
  pull request's body carries the line `Finishes: #<brief>`, a whole stripped line read as
  `brief_of` reads `Brief: #n`. A mention inside a sentence, or a `Finishes:` line naming
  another brief, is not that line; the brief then stays open and gets no comment.
- A brief with a `Builds:` line is closed as before: when every listed build is named by a
  merged pull request's title.
- The comment `All builds merged; last #<pr> <sha12>`, the close as completed, the one GET of
  the brief and every other part of the after-merge step are unchanged.

The existing tests `test_a_one_build_brief_is_closed_after_its_merge` and
`test_the_merge_command_closes_a_finished_brief_after_its_record_line` in
`tests/kit/test_merge_cleared_after.py` gain the `Finishes:` line in their merged body, as the
changed decision requires; their assertions are unchanged.

## Consequences

A brief whose builds are named only in prose stays open after an earlier build merges, and
closes when its last pull request says `Finishes:`, as session rule 28 writes it. A one-build
pull request that omits `Finishes:` leaves its brief open; `doctor.py`'s `brief-finished`
warning names it after a day.

## Residual

- 2026-11-11: brief #846 was closed by the old rule and stays closed until a person reopens it.

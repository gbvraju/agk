# ADR-0411: After a merge, check the issues a pull request closes and close a finished brief (REQ-046)

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0273, SPEC-0039, brief #959, plan #661, issue #614, issue #606
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

A merged pull request names its brief with `Brief: #N`, which GitHub does not read as a closing
keyword, so a brief whose builds had all merged stayed open (#781 after #861, #922 after #928,
#647 after #945) and `session.py plan` listed it under `Skipped:` or as `MALFORMED` until a person
closed it. Issue #614 asked for a check of the closing keywords after a merge.

## Decision

After its record line (SPEC-0039 rule 7), `merge_cleared.py` reads the merged body once more:

- For each issue the body closes with a GitHub closing keyword (`close`, `closes`, `closed`,
  `fix`, `fixes`, `fixed`, `resolve`, `resolves`, `resolved`, any case, an optional colon, then
  `#n`), it waits `CLOSE_WAIT` (5 seconds) once, GETs the issue and, when it is still open, posts
  one comment `Not closed by merge <sha12> of #<pr>; close it if the work is done`.
- For the body's `Brief: #N`, an open issue labelled `agk-brief` whose every build (the
  `Builds:` line, read with `session_plan.builds_of`) is named by the title of a merged pull
  request (`session_plan.names_build`, this pull request's title and the merged pull requests of
  the brief's timeline), or that names no builds, is closed as completed after one comment
  `All builds merged; last #<pr> <sha12>`. A brief with a build unmerged gets nothing.

Every read is one GET, never retried; a read GitHub refuses skips that issue. Every write is one
call, never retried. The merge stands and nothing is held: any error of this step is ignored and
the run goes on to the governance run of rule 6. The merger job runs the same command.

## Consequences

A finished brief leaves the plan when its last build merges, without a person. An issue that a
body says it closes but GitHub left open is named once on that issue.

## Residual

- 2026-11-10: the timeline's merged state is read from `source.issue.pull_request.merged_at` of a
  `cross-referenced` event `(verify)`.

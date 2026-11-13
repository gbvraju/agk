# ADR-0390: The conductor reports a late sweep under `Needs a fix`

- Status: Accepted
- Date: 2026-11-09
- Deciders: maintainers
- Related: ADR-0383, ADR-0310, brief #857, Q-836-1
- Requirements: REQ-046

Protected classes: `.claude/`, `tests/kit/`

## Context

`conductor.py watch` prints `SWEEP late <m> min` when the merger job has gone quiet with a cleared pull request waiting
(ADR-0383 decision 4). The conductor's role file did not say what to do with that line, because `.claude/` was outside
the `Touches:` of brief #836 and ADR-0383 does not name the class (`Q-836-1`). A line that nobody is told to report is
seen only by whoever reads the watch.

## Decision

1. The sentence of `.claude/agents/conductor.md` that puts `MALFORMED:` lines of `session.py plan` under `Needs a fix`
   in every hourly report also names `SWEEP late` lines of `conductor.py watch`. The words `until the brief passes` still
   apply to `MALFORMED:` lines only.
2. The file's rule budget does not grow (ADR-0310): the nine words added are nine words removed from the same paragraph,
   and what that paragraph requires is unchanged.
3. No script changes. `conductor.py watch` prints the line as ADR-0383 decided.

## Consequences

A person reading the conductor's hourly report sees a late sweep in the same hour, under the heading that already
collects what needs a fix. The report repeats the line for as long as `conductor.py watch` prints it. A `SWEEP late` line
names no filer, so `the filer it names` applies to `MALFORMED:` lines only.

## Residual

- 2026-11-09: the sentence is read by the conductor, not by a check; a report that leaves the line out is caught only in
  review.

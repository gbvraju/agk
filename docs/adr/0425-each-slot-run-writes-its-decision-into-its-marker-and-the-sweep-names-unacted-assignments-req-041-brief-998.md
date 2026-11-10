# ADR-0425: Each slot run writes its decision into its marker, and the sweep names unacted assignments (REQ-041)

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0362, ADR-0368, ADR-0402, SPEC-0034, brief #998, plan #661
- Requirements: REQ-041, REQ-054

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

On 2026-11-10 two `Assign:` follow-ups (#965 at 11:38Z, #977 at 13:35Z) were not acted on by the next run of their
slot, and nothing recorded why: a slot run printed its decision only to its own output. Brief #998 asks that each run
write its decision into its own lease marker and that `conductor.py sweep` name an assignment no run acted on. The
marker's shape is a decision of ADR-0362 and ADR-0402 (decision 7), both Proposed, so no Accepted ADR covers this
change and it writes its own (session rule 36); 0425 is the brief's `Reserved:` number.

## Decision

1. A slot's `Slot:` marker keeps its first line as it is and may carry two more lines: `last run: <UTC start> to <UTC
   end>` and `decided: <the last line slot --next printed>`. Every reader matches the first line only, so a marker of
   the older form reads as before.
2. `slot --take` records the run's start beside its run name in the git directory. `slot --next` reads its lease
   without writing, decides, and then writes the lease and the two lines in one edit: the renewal, or, on `stop`, the
   release. `slot --release` writes the run's end and keeps its `decided:` line (`decided: none` when the run decided
   nothing). A renewal with no decision keeps the lines as they are. No run posts a new comment for its log, and an idle
   run costs the same edits as before.
3. A run that finds its slot held by another run, or the switch off, writes nothing, as ADR-0368 decision 2 has it: its
   decision is not logged, since writing into the holder's marker would race the holder's own edit.
4. `conductor.py sweep` ends each slot line with `, last run <hh:mm> decided <...>` when the marker has the lines.
5. After the stall lines, `sweep` prints `UNACTED: <the Assign: line> (<age> min; last run <hh:mm> decided <...>)` for a
   slot's newest `Assign:` by a listed author, other than `none`, when either a run started after it and decided
   something else, or no run started after it and it is more than 75 minutes old; and in both cases only when it is not
   spent: a brief's assignment by a later `taken:` of the slot, a pull request's by a later `Report:` on it. What cannot
   be read adds no line.

## Consequences

- A missed assignment shows within the hour in the conductor's sweep, without one more comment.
- The marker shows the last run only; an earlier run's decision is replaced by the next one.
- A sweep reads one more page of comments per slot with a pending assignment.

## Residual

- 2026-12-31: the conductor's own instructions (`.claude/agents/conductor.md`), outside this brief's `Touches:`, do not
  yet say to list the `UNACTED:` lines under stalls and post the `Assign:` again once (brief #998 answer 3, Q-998-2).
- 2026-12-31: a run that never reaches `slot --next` (a late or killed start) leaves no line; the 75-minute rule is what
  shows it.

# ADR-0403: A session reads only the decisions that name its item, not the frozen log (REQ-052)

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0247, ADR-0277, ADR-0310, SPEC-0045, brief #941, plan #661
- Requirements: REQ-052

Protected classes: `CLAUDE.md`, `tests/kit/`

## Context

The `## Compaction recovery` step of `CLAUDE.md` told every new or compacted session to re-read
`docs/runs/decisions-log.md`. That log is frozen (ADR-0277) and is about 135 KB, so each session
carried tens of thousands of tokens of rulings, nearly all about other items, on every later step.
`CLAUDE.md` is installed, so every project's sessions did the same. On 10 Nov one builder reported
3,660,915 tokens for one 154-line document (brief #941), and the owner asked for the cost to fall.

## Decision

After compaction or a new session, a session re-reads `CLAUDE.md`, its brief, its open pull request
body and only the files under `docs/runs/decisions/` that `grep -l` finds for the brief's number, its
spec ids, its `Q-<N>-` ids and the paths of its `Touches:` line. The old `docs/runs/decisions-log.md`
stays frozen and is read only for a row the brief names. `tests/kit/test_compaction_reads.py` fails
while the step names the old log as a re-read, or does not name the grep of the folder. The writer
rule (a new row is one file under `docs/runs/decisions/`) stays in `.claude/agents/architect.md`.

## Consequences

A session's reading after a restart falls from the whole log to the few files that name its item.
The grep includes the touched paths, so a ruling about a file the build changes is still read; a
ruling it misses is caught at review, as today (`config/review-checklist.md`, the conductor's
`Read:` line). No other rule's meaning changes. `CLAUDE.md` stays at its rule budget line in
`config/rule-budget.txt` (229 words), with three words cut from its opening paragraph. The pinned text in `tests/kit/test_core_rules_page.py` follows the new
section.

## Residual

- 2026-11-24: compare the builders' `Usage:` lines on plan #661 for the two weeks after the merge
  with b798's 3,660,915 tokens before it; the figures are measured, not assumed.

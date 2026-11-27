# ADR-0835: The usage line is split by kind, reads the sub-agents and says why it is not shown

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's yes on brief #2020, 2026-11-26T19:15Z)
- Related: SPEC-0045 rule 8, ADR-0289, ADR-0419, ADR-0544, REQ-052, brief #798, brief #2020, plan #661
- Requirements: REQ-052

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`, `config/`, `kit/`

## Context

Brief #2020 found that 9 of 70 builder `Report:` comments on eight merged pull requests carried a figure. A `not
shown` gave no reason. The figure that was shown was one sum of four kinds of tokens whose prices differ by an order
of magnitude. SPEC-0045 rule 8 counts the session's own transcript only, and a helper agent's tokens only where the
runtime writes them into that file (`Q-798-8`). A builder measured this runtime on 2026-11-26 (`Q-CM-1`). A sub-agent's
transcript is a separate file, `<projects>/<folder>/<session id>/subagents/agent-<id>.jsonl`, beside the parent's
`<session id>.jsonl`. Its entries carry usage records, and the parent's file holds none of them, so the parent's figure
leaves them out.

## Decision

1. `scripts/agk/usage.py` reads the running session's own transcript, or each `--transcript FILE` (which may now be
   given more than once). With `--helpers` it also reads each one's own sub-agent transcripts,
   `<folder>/<stem>/subagents/*.jsonl`. Across all of them each message id is counted once, at its first entry. A
   sub-agent's environment carries its parent's session id and no id of its own (measured 2026-11-26). So the sub-agent
   files are read only when the session asks for them, and only the top-level session does; a sibling's tokens never
   enter another sub-agent's line, and each token is counted once (SPEC-0049 rule 4). The top-level builder's
   prompt (`kit/templates/runtime/builder.txt`) ends its `Report:` with the line `usage.py --helpers --since
   <previous Report:>` prints, and `steward.py end` reads with `--helpers`. This changes `Q-798-8` of SPEC-0045
   rule 8 (amendment 263).
2. Its line is `Usage: <n> tokens (input <a>, cache write <b>, cache read <c>, output <d>)`. `<n>` stays the sum, so a
   reader that takes `<n>` reads the same figure. A whole count of 0 or more under any other `*_tokens` key of a usage
   record whose key names no cache (so a flattened cache-creation count is never counted twice) is summed in `<n>` and
   named `, other <e>` when it is not 0.
3. With no figure the line is `Usage: not shown (<class>)`. The class is `no-session-id` (no named file and no valid
   session id), `no-transcript` (a file not found), `unreadable` (a file that cannot be read as text) or
   `no-usage-record` (no usage record, or none at or after `--since`). It never names a path, an id or a value
   (principle 8). One unreadable file gives `unreadable` for the whole line, so a short sum is never printed.
4. The readers of the line accept the new ending: `metrics.usage_of` (`Report:` lines), `session.PROGRESS` and
   `caps.PROGRESS_USAGE` (`Progress:` lines). Session rule 17 names the ending (`split or classed`), rule 32 no longer
   restates `Usage: not shown`, and rule 8 takes `usage.py`'s line as printed. `config/rule-budget.txt` is lowered to
   the file's new count (3605). Amendment 263 proposes the same lines for SPEC-0045 rule 8.
5. `steward.py end` without `--tokens` writes, with its own sub-agents, `tokens <n> (input <a>, ...)` or `tokens not shown (<class>)` from the
   same reader. A typed `--tokens` is used as before.

## Consequences

A report's figure says what kind of tokens it holds, a session that uses helper agents reports their tokens too, and a
missing figure says why. Protected path classes changed: `scripts/agk/` (`usage.py`, `metrics.py`, `session.py`,
`steward.py`, `caps.py`), `tests/kit/` (`test_usage_split.py`, `test_usage_transcript.py`), `agk.toml` (the new test
file in the `[[testing.map]]` entries of `usage.py`, `metrics.py`, `session.py` and `steward.py`) and `config/`
(`config/session-rules.md` rules 17 and 32, `config/rule-budget.txt`) and `kit/` (`kit/templates/runtime/builder.txt`,
the `Report:` line).

## Residual

- 2026-11-26: `Q-2020-1`: answers 3, 4 and 6 of brief #2020 (a price table by kind under `[models.prices]`, the sums
  by pull request, brief, role and stage, and the weekly coverage line) overlap ADR-0544's `[cost.prices.<model>]`
  table and `metrics.py --cost`. They wait for the maintainers' ruling and are not built here.
- 2026-11-26: a builder that itself runs as a sub-agent finds the parent's file through the parent's session id
  (measured: the runtime gives it no id of its own), so its line holds the parent's own figure, not its own; a way
  for it to find its own file is left open. A steward or builder started as a sub-agent from the prompts that pass
  `--helpers` would count the parent's and its siblings' tokens, so such a run should drop the flag (verify: no
  launcher starts one today).
- 2026-11-26: the conductor's `Conductor report` (answer 5) is written from `.claude/agents/conductor.md`, a path class
  the brief's `Touches:` does not name, and is not changed here.

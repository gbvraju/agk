# ADR-0544: The day's model spend is read from local usage records

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: brief #1283, brief #798, ADR-0419, plan #661
- Requirements: REQ-050

## Context

Brief #1283 found that a customer project on AGK spent about 250 USD of API credit in one day with a conductor and two
builders, and nobody could say which session, role, brief or model spent it: builder reports carry `Usage: not shown`,
so `metrics.py --usage-by-kind` (brief #798, ADR-0419) has no figures. The runtime keeps a per-turn record of each
session on the machine, one JSON entry a line, with each reply's model and token counts `(verify: the folder
`<CLAUDE_CONFIG_DIR or ~/.claude>/projects/**/*.jsonl` and the fields `cwd`, `gitBranch`, `sessionId`, `timestamp`,
`message.id`, `message.model` and `message.usage` with `input_tokens`, `output_tokens`, `cache_creation_input_tokens`
and `cache_read_input_tokens` were read from this cloud runtime's own records, not from its documentation)`.

## Decision

1. `scripts/agk/metrics.py --cost [--day YYYY-MM-DD] [--days N] [--records DIR] [--save]` reads the record files under
   `--records DIR`, else `<CLAUDE_CONFIG_DIR>/projects`, else `~/.claude/projects`, written on or after the first day
   asked. Of an entry it reads only the named fields above, with a `.get` of each key; it never reads a message's
   content and never walks an entry. It makes no network call. The options go with `--cost` alone.
2. A reply is an entry of type `assistant` with a message id, counted once at its first entry (a reply written in
   parts shares its id). It is this clone's when its `cwd` is the clone's folder, one of its worktrees (`git worktree
   list`) or a folder under one; any other reply, or one with no `cwd`, is skipped and counted on the `Skipped:` line.
3. Each reply is grouped by session (`sessionId`, else the file's name), role, brief and model. The role is the
   session's agent name when an entry field names one of conductor, builder, steward, reviewer, shadow or architect,
   else `builder` on a `claude/brief-<n>` branch, else `unknown`. The brief is `#<n>` of a `claude/brief-<n>` branch,
   else of a `brief-<n>` worktree folder, else `unknown`. A session id or model that is not a plain identifier is
   `unknown`, so no free text is printed.
4. One table per day (UTC), oldest first: a row per group with its replies and the four token kinds and their total,
   then the day's total, the top five sessions and briefs by tokens, and the share of cache reads against fresh input
   (input plus cache write) over the input-side tokens.
5. USD comes only from the optional `[cost.prices.<model>]` tables of `agk.toml`, each kind (`input`, `output`,
   `cache_write`, `cache_read`) a price per million tokens of 0 or more; the kit ships no price. A bad table or price is
   refused naming the setting, never the value. Without a table the rows show `-` and one line `usd: not priced`; a
   model with no price, or a priced kind missing, is `unknown`.
6. A count that is missing or not a whole number of 0 or more is `unknown`, and so is every sum it enters, never 0; a
   line that is not JSON is counted as unreadable; a record file or folder that cannot be read is counted on the
   `Skipped:` line and marks the day's total `(at least: <n> record files could not be read)`, so a short total is
   never silent; a day with no reply of this clone prints `Total: unknown`.
7. `--save` writes each day's figures, numbers and identifiers only, to `docs/runs/cost/<date>.json`.

## Consequences

A person can see where a day's spend went from the machine that ran the sessions, without any session reporting it.
A record kept on another machine is not seen, and the conductor's hourly line `Spend today:` waits until its guard
allows the command. Protected path classes changed: `scripts/agk/` (`metrics.py`), `tests/kit/`
(`test_metrics_cost.py`) and `agk.toml` (the new test file in the `[[testing.map]]` entry of `metrics.py`).

## Residual

- 2026-11-15: Q-1283-1: the records read on this runtime carry no field naming the session's agent, so a conductor or
  steward session on the default branch shows role `unknown`; the agent fields read are marked (verify).
- 2026-11-15: the conductor's hourly report line `Spend today:` (brief #1283 answer 3, "may add") is not built here.

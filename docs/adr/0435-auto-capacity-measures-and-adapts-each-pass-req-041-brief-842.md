# ADR-0435: The `auto` capacity profile measures the machine and adapts by evidence each pass

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: SPEC-0034 rule 15, amendment 149 items 4 to 6, ADR-0409, ADR-0384, ADR-0223, brief #842
- Requirements: REQ-041

Protected classes: `agk.toml`, `scripts/agk/`, `tests/kit/`

## Context

Amendment 149, applied to SPEC-0034 on the owner's `Approve:` lines, makes `auto` the default profile of the
`[capacity]` table: measured each pass and adapted by evidence. Build (b) (ADR-0409) built the table and the other
profiles and left `auto` reading as no table (its decision 3) and `builders_run` refused (its decision 1). This is
build (c), items 4 to 6; it changes those two decisions of ADR-0409, so it writes its own ADR (session rule 36).

## Decision

1. `config.py` accepts `[capacity] builders_run = "here" | "cloud"` (`here` when unset, Q-842-3); another value is
   refused as `setting: capacity.builders_run`. This replaces ADR-0409 decision 1's refusal.
2. Under `auto`, `session.py plan` measures available memory over `builder_memory_gb`, free cores over
   `builder_cpus` and free disk under the repository over `builder_disk_gb`, each only where its setting is set,
   rounded down, with no reserve and the floor of 1 while no builder runs (ADR-0223). With `builders_run = "cloud"`
   no machine figure is read. This replaces ADR-0409 decision 3 for `auto`; `none` is unchanged.
3. The record: `plan --record` under `auto` appends one JSON line per pass (`at`, `count`, `change`, `why`) to
   `docs/runs/capacity-record.jsonl`, added to the clone's own `.git/info/exclude`, as the holds record is (Q-842-2,
   Q-772-1). `plan` alone reads it and writes nothing; no check reads it.
4. The count. The highest is the smallest of `max_builders` and, for each measured figure, the running builders plus
   the builders it has room for. With no record the count is the highest. Otherwise, from the record's last count,
   as amendment 149 item 5 lists them: one less, never below 1, after a reason to drop (reviews over `review_minutes`,
   or memory or disk under its reserve); else one more, never above the highest, when the rise conditions that can
   be read all hold and at least one of them can be read; else the same, capped at the highest. The rise conditions
   are `checks` (the newest of the last 20 successful `governance` runs within 1.5 times their median, unread with
   fewer than 20, Q-842-6) and `reviews` (the median of the last 10 times from a `Report:` that asks for a verdict to a
   listed author's `Verdict:` on its head, read from the 30 newest pull requests, under `review_minutes`). Slow checks
   and reviews at exactly `review_minutes` stop the rise and never drop the count. The reserve (the free memory or
   disk, where measured, under a quarter of the machine, Q-842-5) is only a reason to drop, never to rise. `starts`
   always reads `unknown`: a refused start is recorded nowhere (Q-842-8). A verdict that names a short head answers
   the newest `Report:` whose head it matches.
5. The output. With a record the count is one more limit, `adapt`, so `Capacity:` and `Start 0` name it with its
   figure (`limit: adapt 2 drop: reviews`). Under `auto` the JSON carries `adapt` with the count, the highest, the
   change, the reason, each condition and the last 20 changes, and the words print `Adapt: <n> of <highest> (<why>).`
6. `agk.toml` maps `tests/kit/test_capacity_adapt.py` to `config.py` and `session_plan.py` in `[[testing.map]]`.

## Consequences

A project on `auto` with no per-builder setting starts what it started before. With settings, a small machine starts
fewer builders, and a team that runs `plan --record` sees the count fall after slow reviews or checks and rise back by
one a pass. The plan reads GitHub once more for the governance runs and once per recent pull request, only when a
record exists.

## Residual

- 2026-11-11: refused starts read `unknown` until a person names their source (Q-842-8), so a cloud project adapts on
  reviews and checks alone.

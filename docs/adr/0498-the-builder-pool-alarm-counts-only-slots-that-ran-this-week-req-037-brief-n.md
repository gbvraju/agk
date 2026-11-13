# ADR-0498: The builder pool alarm counts only slots that ran this week

- Status: Accepted
- Date: 2026-11-13
- Deciders: maintainers
- Related: brief #1172, plan #661, issue #1159, issue #1028, ADR-0368, ADR-0412, ADR-0487
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

`conductor.pool_state` opens `Builder pool down` when more than a third of the slots named by `builder_slots` were not
seen within `slot_seen_minutes` (ADR-0412), and it counts a slot that was never seen as dead. This repository's slots
s1 to s9 last ran on 2026-11-10 and were retired when builders became cloud sessions started by the conductor; after
`max_builders` rose to 12 (ADR-0487), #1159 listed all 12 slots dead, s10 to s12 `never`, and a hand close does not hold:
the router opens it again on its next run. Any project that retires its slots, or raises `max_builders` above the slots
it runs, gets the same false alarm.

## Decision

1. In `conductor.pool_state` a slot counts toward the alarm only when it holds a valid lease or its lease marker shows it
   ran within the last `slot_active_days` days, a new optional key of the `[flow]` table of `agk.toml`: a whole number of
   1 or more, default 7. Another value is refused with `setting: flow.slot_active_days`, never the value; the router's
   health step then skips and writes nothing, as for an unreadable lease (ADR-0412 point 4).
2. A slot never seen, or last seen before that, is listed as retired in the issue's text, with the time it was last
   seen or `never`, and is not counted. The alarm is down when more than a third of the counted slots were not seen
   within `slot_seen_minutes`; when no slot counts it is off, and an open `Builder pool down` issue closes as before.
3. Nothing else changes: the 90-minute window of ADR-0412, the one-third share, the `No live conductor` row and
   `builder_start = "start"`, which turns the pool rows off.

## Consequences

A project that moved from slots to conductor-started builders stops getting `Builder pool down` once its slots are
older than `slot_active_days`, and a slot that never ran never raises it. A pool whose slots stop for longer than a week
also raises no alarm after that week; the issue's text names those slots as retired. Two existing tests whose third
slot was never seen now give it a run 91 minutes ago, so they still count three slots.

## Residual

- 2026-11-13: this repository's slots last ran on 2026-11-10, so with the default the alarm closes from about
  2026-11-17 22:06Z; a smaller `slot_active_days` in `agk.toml` closes it sooner, a protected change left to the owner.

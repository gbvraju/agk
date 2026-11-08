# ADR-0368: A dead lease holder is replaced in minutes, and a dead conductor or pool is reported (REQ-041)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0330, ADR-0353, ADR-0362, SPEC-0034, SPEC-0032, ADR-0207, brief #776, plan #661
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`, `.github/`, `.claude/`

## Context

Brief #776 answer 5 asks that a dead conductor or a dead builder pool be reported with no session running, and its
addition of 2026-11-08 09:36Z, on the owner's direction, gives the evidence: `conductor-0848` stopped at about 09:10Z
while its lease ran to 09:59Z, so the relay starts at 09:18Z and 09:33Z found it held and ended; #766 waited 25 minutes.
ADR-0330, ADR-0353 and ADR-0362 set both leases to 50 minutes. This build changes that decision and a workflow, so it
writes its own ADR (session rule 36). The brief names no number for it; 0368 is what `session.py ids` printed.

## Decision

1. Both leases are valid 10 minutes, not 50: `Conductor:` (ADR-0330) and `Slot:` (ADR-0362). This replaces those two
   numbers and nothing else of those ADRs.
2. `conductor.py watch` renews this checkout's lease at every pass, at most every 4 minutes, and returns within 5
   minutes with `nothing new`. Another name holding the lease ends it with exit 3, writing nothing.
3. `session.py watch --assign <slot>`, for a slot of a pool (`builder_start = "assign"`, the name `s<n>`), renews the
   same way, returns within 5 minutes with `no event`, and ends with exit 3 when another run holds the slot. A session
   that is no slot keeps its long wait and `assign-timeout`.
4. A run releases its lease on every exit path it can reach: `slot --next` on `stop` and a slot's watch that ends
   because GitHub cannot be read release it in the command; the conductor is told so in `.claude/agents/conductor.md`,
   a refused action included. A release that cannot be written is left to expire within 10 minutes.
5. With `builder_start = "assign"`, every run of the router job (`route.py`, `agk-route.yml`) reads the two leases and
   opens, updates or closes one plain issue per kind, label `agk-health`, never a brief: `No live conductor` when
   `plan_issue` is set, no valid lease exists and a brief or a ready pull request waits; `Builder pool down` when
   more than a third of `builder_slots` have no valid lease and a brief waits. Each closes when its leases are back, and
   stays open while they are missing even if the work is gone. A lease that cannot be read writes nothing and fails no
   routing. `route.py --health` is the same check where no job runs (local mode).
6. `agk-route.yml` also starts on a comment whose first line is `Assign:` or `Request:`, because a dead pool pushes
   nothing and these are its only events. The owner's yes to this workflow change is quoted in brief #776; the owner merges it.
7. `conductor.py sweep` lists every slot: `working (#n)`, `idle`, `dead since <time>` or `dead (no lease yet)`.
8. With `builder_start = "start"` none of the health reads or lines happens. The shorter leases and the conductor's
   5-minute bound hold in both, since the addition states them without that condition.

## Consequences

- A dead holder blocks a staggered start for at most 10 minutes, so it is replaced within about 15.
- A conductor wakes at least every 5 minutes, also with nothing new, which costs a turn each time.
- Each `Assign:` and `Request:` comment bills one minute of the router job (ADR-0207).
- No session is needed to learn that the conductor or the pool is down, so long as some event still happens.

## Residual

- 2026-12-31: a run that works for more than 10 minutes between two watches lets its lease lapse: a conductor mid-review or a
  slot mid-build must renew by hand (`lease --take <name>`, `slot --renew`), or a staggered start joins it (Q-776-5).
- 2026-12-31: with no event at all (no push, no comment) nothing wakes the router, so a repository fully at rest reports
  nothing; a schedule would close that and would bill a minute per run (Q-776-6).
- 2026-12-31: the exits the kit cannot see (a killed session) rely on the 10-minute expiry, which is what it is for.
- 2026-12-31: a run that releases its lease at the end of its window leaves a gap until the next staggered start; with
  `assign`, any event in that gap opens `No live conductor`, which notifies the owner, and the next event closes it.
- 2026-12-31: the router's concurrency group is per issue or pull request, so two events at once can each find no open
  health issue and open two, which decision 5's "one plain issue per kind" does not allow for.

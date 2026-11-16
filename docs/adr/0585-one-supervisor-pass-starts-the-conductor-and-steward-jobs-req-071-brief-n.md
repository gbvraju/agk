# ADR-0585: One supervisor pass starts the conductor and steward jobs, once per event, within the stop rules

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1387, SPEC-0064 rules 2, 6, 12, 14, 15 and 16 (b), brief #1386 (ADR-0584), brief #1310 (ADR-0554), brief #1359 (ADR-0571), brief #1355 (ADR-0568), brief #1322 (ADR-0559), SPEC-0063 rule 4, plan #661
- Requirements: REQ-071

## Context

SPEC-0064 (Approved) puts one supervisor per machine, with no model, in charge of starting every AI session as a
short job. Build (a) gave each job a record and `agk status`. Today `conductor.py watchdog --pass` (ADR-0554) runs
the plan, the sweep and the review queue on every pass, so a quiet pass still costs dozens of GitHub calls on a
large project; the conductor's role file paces a hand-started conductor with `/loop`; the conductor starts the steward
on a `STEWARD:` line and the steward starts the conductor with `steward_owner.py ready --start` (SPEC-0059 rule 2,
ADR-0559); and nothing says why the supervisor starts nothing.

## Decision

1. **The supervisor pass (rule 2).** `watchdog --pass` holds the machine's `lock.py` lock `autopilot` for the pass
   (waiting at most 120 s for another pass, then starting nothing, exit 0). Before taking the lease it reads the
   open pull requests and, when its last full read is younger than 30 minutes, the issues and the comments changed
   since then (`session.changed_comments`, #1314's delta read); when nothing changed (the lease marker's own
   edits and the plan issue's own update are no change, and the pull requests' numbers, heads, drafts and labels
   are the same) it prints `watchdog: nothing changed; no job started`, takes no lease and reads neither the plan
   nor the sweep. A full read follows at least every 30 minutes, for the waits that age (a question waiting one
   pass). An event, a new comment, issue change or head, starts its job within one pass. The quiet check is never
   used before a first full read or while the 24-hour job of ADR-0554 is due outside a stop rule.
2. **The steward job (rule 6).** A `STEWARD:` line of the sweep starts one steward job through `launch.py role`
   with `AGK_STEWARD_START=conductor` in its environment, and its prompt says to answer from evidence only, relay
   nothing and approve nothing; `steward_owner.py relay` refuses under that marker (exit 2). No steward job starts
   while a steward is open on the machine (a live job record of kind `steward`, or a `claude --agent steward`
   process), or for a session this machine started within the hour.
3. **The two starts become the supervisor's (rule 14).** `steward_owner.py ready --start` with `auto_start` and
   `launch_adapter` set starts nothing itself and prints that the supervisor's next pass starts the conductor; the
   plan's start is the pass's trigger. The conductor's role file starts no steward on a `STEWARD:` line. The
   conductor's builder starts stay its own until build (c).
4. **The conductor's cadence (rule 15).** `.claude/agents/conductor.md` drops `/loop` and the self-paced wake: the
   supervisor starts the conductor as a short job of one pass, and a hand-started conductor runs one pass and ends.
   The `ScheduleWakeup` tool and the operating lesson that names a wake-up timer are left as they are (a rule line;
   cutting it is not this build's).
5. **The stop rules (rule 12).** After a full read with something to do, no job starts when the review queue is
   empty, the plan starts nothing and no question waits: `every remaining item waits on the owner` when the sweep
   prints a `NEEDS-YOU:` line, else `no brief is ready and nothing waits on AGK`; nor below 200 core calls left
   (`the GitHub limit is low`, `GET rate_limit`). Paused and free memory below one builder stay the pass's own
   checks. No job of this build is an owner-only step, so `owner_rest_hours` stops none (Q-S0064-3). The reason
   is printed once, `watchdog: quiet: <reason>`, kept in `<git dir>/agk/watchdog.json` and shown by `agk status`
   as `quiet: supervisor: <reason>`.
6. **Health (rule 10).** Each pass appends one line to the temp folder's health file through ADR-0584's
   `append_health`, with the jobs it started by kind.

Protected path classes changed: `scripts/agk/` (`conductor.py`, `launch.py`, `steward_owner.py`, `autopilot.py`),
`.claude/` (`agents/conductor.md`, `agents/steward.md`), `config/` (`rule-budget.txt`), `tests/kit/`
(`test_autopilot_supervisor.py` and the tests of the changed texts and fixtures),
`agk.toml` (the `[[testing.map]]` entries), `docs/adr/` (this file) and `changelog.d/` (one fragment).

## Consequences

A quiet pass costs a handful of calls and no model; an event starts its job at the next pass. A machine whose
scheduler runs no `--pass` no longer gets the conductor from `ready --start` or the steward from the conductor:
`watchdog --install --pass` prints the line that sets it up.

## Residual

- 2026-11-16: the stop rule's line goes into `agk status` only; the steward's daily list does not carry it yet
  (Q-1387-1) (due 2027-03-31).
- 2026-11-16: an open steward on another machine is not seen; its `steward.py start` refuses a second steward,
  posting nothing (due 2027-03-31).

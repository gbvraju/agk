# ADR-0402: The conductor assigns its builders, and a stall is seen on a tick and acted on (REQ-041)

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: ADR-0330, ADR-0353, ADR-0362, ADR-0368, SPEC-0034, brief #776, plan #661
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`, `.claude/`, `agk.toml`

## Context

Brief #776 build (c) is the last of its Plan: the conductor's switch to `Assign:` lines, answer 4 (the schedule and the
doctor's check, left over by builds (a) and (b)) and the brief's additions of 2026-11-08 11:20Z, 2026-11-09 04:43Z and
2026-11-09 13:25Z. The evidence is the brief's: three drafts idle 29 to 52 minutes with no line from the conductor;
`conductor-7adeec93` renewing its lease for 52 minutes with no verdict, while #813 waited for one for 7 hours;
`conductor-11091233` ending early with its lease renewed for almost an hour after, and two relays exiting on it.
The brief reserves ADR-0362 and amendment 143, which builds (a) and (b) already used. This build changes decisions of
ADR-0330 and ADR-0368 (a held lease can be taken over; `watch` ends with `tick`), so it writes its own ADR (session
rule 36); 0402 is what `session.py ids` printed. It adds items to amendment 143.

## Decision

1. With `builder_start = "assign"`, `session.py plan` has an empty `start` list and an `assign` list of the free slots,
   each row with its `line`, `Assign: <slot> #<brief> [build (<x>)]`; `launch.py` therefore starts nothing. A slot with a
   live take is not free, and the rows are capped by the free slots. With `start` the plan is what it was.
2. This repository sets `builder_start = "assign"`. `builder_slots` stays unset, so it is `max_builders`.
3. `doctor.py` has one warning, `slot-schedule`: with `assign`, its message prints each slot's four staggered minutes and
   slots times starts per hour, and it fails naming a slot with no `Slot:` marker written in the last hour. The kit cannot
   read an account's scheduled tasks, so a slot's own marker is the evidence that its schedule runs.
4. `conductor.py watch` ends within 5 minutes with no event with the line `tick` (it was `nothing new`, which `--once`
   keeps), followed by the stall lines. `sweep` prints the same lines.
5. A draft of a builder (a `Brief:` line) gets `STALL #<pr> <m>m: restart <session>` when neither a push nor a `Progress:`,
   `Report:` or `Question:` comment came for `[flow] stall_minutes` (30), and `STALL #<pr>: failed check <name>` when a
   required check failed and no `Progress:` came for 15 minutes. A draft whose newest comment is a `Question:` waits for
   an answer and is not stalled, and what cannot be read is never a stall.
6. On a refused start the conductor posts one `Owner needed:` on the pull request; the `STALL` line then ends
   `(owner needed posted)`, which is what stops a second one, and stays until a builder reports. With `assign`, the start
   is an `Assign:` line, which cannot be refused.
7. `lease --take` records the time of the take in the marker (`Conductor: active <time> <name> since <time>`), and a
   renewal keeps it. Over `stall_minutes` since the later of that time and the holder's last conductor comment (first line
   `Verdict:`, `Assign:`, `Tell:`, `Correction:`, `Owner needed:`, `STALL ` or `Conductor `), with a review or a start due,
   the holder is stalled: `sweep` and a tick print `STALL conductor <name> <m> min`, and another name's `lease --take` posts
   that line on the plan issue and takes the lease. A renewal by a watch never takes over.
8. A run that ends releases its lease in the same step, before its report, and the report says `lease released`
   (`.claude/agents/conductor.md`).
9. A red-branch issue closed since the watch began ends it with `MAIN GREEN after #<n>: merge of main #<pr> (<session>) ...`,
   naming the open pull requests whose every failed check finished while the issue was open. The pass starts each merge
   of main (with `assign`, `Assign: <slot> #<brief> pr #<n> merge of main`).

## Consequences

- No conductor starts a builder here, so nothing depends on a session's permission to start one; the owner has to create
  the schedules `doctor.py` prints, and until they run `Builder pool down` is open and no brief is built.
- The conductor spends a turn on each tick, and a tick's lines cost a few reads per draft.
- The marker has one more field; a marker of the older form counts from its own time and is never read as a stall.

## Residual

- 2026-12-31: builders and the conductor post under one account here, so the holder's comments are told apart by their
  first lines; a conductor comment in another form is not seen and can make a live holder read as stalled, and a takeover
  then ends its next renewal with exit 3.
- 2026-12-31: a slot's marker shows that some run renewed it, not which schedule did: a slot that runs on three of its four
  starts passes the check.
- 2026-12-31: "only failure was the red main" is read from the times of the failed checks, so a pull request's own failure
  inside the window also gets a merge of main; a rerun on the merged head then shows it.
- 2026-12-31: a review due is a ready report with no verdict on the head, and a start due is the plan's own list; a brief
  that only waits for a dependency is not due, and a plan that cannot be read says nothing is due.

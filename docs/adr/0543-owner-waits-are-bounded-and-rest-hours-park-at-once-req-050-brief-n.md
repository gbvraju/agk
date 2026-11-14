# ADR-0543: Owner waits are bounded in minutes and rest hours park at once

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: brief #1282, brief #1277, brief #1245, brief #1043, brief #615, ADR-0301, ADR-0442, ADR-0453
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

In a customer project on v0.64.2 (local mode, 2 builders), two pull requests sat on owner questions while
their builders each kept a slot, and a third brief waited with `no free slot`. A builder whose question is
`for the maintainers` holds its pull request and its slot until an answer comes. `agk:parked` exists, but only a
person sets it. The owner (brief #1282, quoted there) asked that such work pause and move on after a
configurable number of minutes, or at once during the owner's configured rest hours.

## Decision

1. `[flow]` gains three keys, read only from the real `[flow]` table (`config.owner_wait_settings`):
   `owner_wait_minutes` (30; 0 parks at once), `owner_rest_hours` (empty; `"HH:MM-HH:MM"`, which may cross
   midnight, the end not included) and `owner_utc_offset` (`"+00:00"`, a fixed `"+HH:MM"` or `"-HH:MM"`, so no
   time-zone database is needed). A bad value is refused naming `setting: flow.<key>`, never the value. The three
   keys join `TABLE_KEYS["flow"]`.
2. A pull request waits on the owner when its newest open item is a `Question: Q-… for the maintainers` (until
   an `Answer:` naming its id, a `Correction:` naming it, or a `Maintainer answer:` or `Approve:` by a listed verdict
   author or spec approver), an `Owner needed:` by a listed verdict author (until such an answer), or the
   router's `agk:approve` or `agk:owner-merge`, timed from the newest comment (`session.owner_item`). Its key is the
   Q id, else `owner-needed`, `approve` or `owner-merge`. A new push does not close the wait: the builder keeps
   working on what the question does not block.
3. Outside rest hours the wait is `owner_wait_minutes` from that post; inside rest hours it ends at once
   (`session.owner_step`). Then `session.py watch --pr N` and `conductor.py sweep` park the pull request: one
   label write (`agk:parked`) and one comment `Parked-by: wait <key>`. `watch` prints `parked #<n> <key>` and a
   `next:` line naming `Report: <head> handing over: blocked: <key> waits for the owner` and
   `session.py after --session <ID>`. Nothing is closed.
4. A parked pull request holds no builder slot: `next`, `demand`, the plan's running count and a slot's owned
   pull requests leave it out (`session.running_builders`). Its take stays live, so no other builder takes its
   brief.
5. When this rule parked the pull request (its newest `Parked-by: wait` comment is newer than any
   `Unparked-by:`) and an answerer has since posted a `Maintainer answer:`, `Answer:`, `Approve:` or
   `Correction:`, the next sweep removes the label and posts one `Unparked-by: answer <key>`. That comment
   marks the label as no longer this rule's, so a person's later `agk:parked` is never read as one. A person's
   own `agk:parked` (no such comment) is never removed.
6. `sweep` prints `UNPARKED #<n> <key>; run: python3 scripts/agk/session.py resume --pr <n>` and `PARKED #<n>
   <key>` before its `START` lines. It lists each park once, by its comment's id, kept in the `parked` mark
   beside the conductor's lease mark. `session.py next` offers an unparked pull request whose author has not
   spoken since the `Unparked-by:` first, before stalled pull requests and new briefs.
7. Personal mode has no pull requests: the wait applies only to a brief's question, which is printed, and
   nothing is parked.

## Consequences

An owner question no longer holds a builder slot for longer than the configured wait. With
`owner_rest_hours = "20:00-08:00"` and `owner_utc_offset = "+05:30"`, a question at 22:00 parks at once and frees
the slot. The router already keeps `agk:parked` as a person's hold and never sets or removes it. After the
unpark, the hand-over `Report:` makes the router show `agk:handover`. `session.py` gains three POSTs and one
DELETE, all on the pull request of the wait.

## Residual

- None.

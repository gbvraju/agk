# Proposed spec amendments 143 (SPEC-0034; REQ-041)

Date: 2026-11-08 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0362 (brief #776), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md`. The number 143 is the one brief #776
reserved. This amendment is not applied to the spec text in this pull request; the owner decides it, and it needs a
person's `Approve: SPEC-0034`; no session posts it. Items 1 to 3 are built by build (a); builds (b) and (c) add theirs.

1. **The setting.** `[flow]` gains `builder_start`, `start` (the default) or `assign`, and `builder_slots`, a whole
   number of 1 or more, by default `max_builders`; slots are named `s1` to `s<n>`. A bad value is refused naming the
   setting, never the value. With `start` nothing changes and `session.py slot` exits 3 without a call.
2. **The slot lease.** `session.py slot --take|--renew|--release <slot>` keeps one marker per slot on the one open
   `agk-conductor` issue, first line `Slot: active|released <time> <slot> <run>`, by a listed verdict author, edited in
   place, valid 10 minutes (item 6). A run that finds its slot held exits 3 and writes nothing. The oldest marker of a slot decides, and a take
   reads it back.
3. **The slot's loop.** `session.py slot --next <slot>` renews the lease and prints one step: `stop` on `Pool: stop` by
   a spec approver; `follow-up pr #n <why>` for a conflict or an unanswered fix list on a pull request the slot owns, or
   for `Assign: <slot> #<brief> pr #<n> <fix list|merge of main>` with no later `Report:`; `assign #b [build (x)]` for
   the newest unspent `Assign:`; `wait pr #n` while it has an open pull request (rule 3 stands); `take` (`next --take`)
   when the conductor has assigned nothing for 10 minutes, counted from the newest `Request:` or `Assign:` of the slot;
   `wait`; or `request` with neither. A slot ends when its window ends or on `stop`.
4. **The POSTs (rule 12).** Rule 12's list of POSTs gains the slot marker of item 2.
5. **Tests.** Rule 14's list gains: assignment to a slot; a held slot ends the run; follow-ups before new work;
   `next --take` only after 10 idle minutes; `builder_start = "start"` unchanged.
6. **The shorter leases (ADR-0368, build (b)).** Item 2's 50 minutes is 10, and the conductor's lease is 10 too. A slot's
   `watch --assign` and `conductor.py watch` renew at every pass and return within 5 minutes with no event. A run
   releases its lease on every exit path.
7. **Health (ADR-0368, build (b)).** The router job reads both leases on every event and opens, updates or closes the plain
   issues `No live conductor` and `Builder pool down` (label `agk-health`); `route.py --health` is the same check with no
   job. `sweep` lists each slot as working, idle or dead since when. With `builder_start = "start"` none of this runs.
8. **The conductor assigns (ADR-0402, build (c)).** With `builder_start = "assign"`, rule 15's plan has no sessions to start:
   an `assign` list names the free slots, each row with its `Assign:` line, and the conductor posts those lines. Follow-ups are
   `Assign: <slot> #<brief> pr #<n> <fix list|merge of main>`.
9. **The schedule (ADR-0402).** Each slot runs from four staggered scheduled starts an hour; `doctor.py` prints them and warns
   of a slot with no `Slot:` marker written in the last hour.
10. **Ticks and stalls (ADR-0402).** `conductor.py watch` ends with `tick` within 5 minutes with no event, and `sweep` and a tick print
    `STALL #<pr> <m>m: restart <session>`, `STALL #<pr>: failed check <name>` and `STALL conductor <name> <m> min`. One `Owner
    needed:` per refused start.
11. **Takeover (ADR-0402).** Another name may take a lease whose holder has made no conductor comment for `stall_minutes` with a
    review or a start due, after posting the `STALL conductor` line on the plan issue. A run that ends releases its lease before its report.
12. **Main green (ADR-0402).** A red-branch issue closed ends the watch, naming the pull requests whose every failed check finished
    while it was open; the pass starts their merge of main.

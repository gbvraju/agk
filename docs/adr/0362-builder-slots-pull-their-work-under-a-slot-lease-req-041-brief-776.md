# ADR-0362: Builder slots pull their work under a slot lease; the conductor assigns and never starts a session (REQ-041)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0125, ADR-0130, ADR-0330, ADR-0353, SPEC-0034, brief #776, plan #661
- Requirements: REQ-041

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

On 2026-11-08 the conductor started 9 builders by starting the builder task, and every start from 07:05Z (3 of 3) was
refused by the session's automatic permission check; a person started them by hand. A session that starts a session
depends on that check. The kit already has the pull model (`Request:` and `Assign:` on the assignments issue,
`session.py watch --assign`, `session.py next --take`, SPEC-0034, ADR-0125, ADR-0130). What it lacks is a standing,
named builder that a schedule can restart, and a way to know one is alive.

## Decision

1. `[flow] builder_start` is `start` (the default, today's behaviour) or `assign`. `[flow] builder_slots` is a whole
   number, 1 or more, by default `max_builders`. Slots are named `s1` to `s<n>`. With `start` there are no slots:
   `session.py slot` says so, calls nothing and exits 3.
2. `session.py slot --take|--renew|--release <slot>` keeps one marker comment per slot on the one open `agk-conductor`
   issue, first line `Slot: active|released <time> <slot> <run>`, by a listed verdict author, valid 50 minutes like the
   conductor's lease (ADR-0330). The run name is minted at the first take and kept in the git directory. A run that
   finds its slot held by another run exits 3 and writes nothing. Two takes at once are settled by reading the marker
   back: the oldest marker decides, and the loser exits 3.
3. `session.py slot --next <slot>` is one pass of the slot's loop: it renews the lease (exit 3 when the run no longer
   holds it) and prints the one next step as its last line, reading only GitHub. In this order: `stop` when `Pool: stop`
   is posted on the assignments issue by an account in `spec_approvers`; `follow-up pr #n conflict|fix list` for an
   open pull request of a brief the slot has a live take of; `follow-up pr #n <fix list|merge of main>` for a newest
   `Assign: <slot> #<brief> pr #<n> <fix list|merge of main>` with no `Report:` on that pull request after it;
   `assign #b [build (x)]` for a newest `Assign:` not yet spent (`spent` as in `watch --assign`); `wait pr #n` while the
   slot has an open pull request and nothing is owed on it; then, with none of those, `take` (run `next --take`) when the
   newest `Request:` or `Assign:` of the slot is 10 minutes old, `wait` before that, and `request` when the slot has
   neither. `ASSIGN` and `watch --assign` take the follow-up form as well.
4. Builds (b) and (c) of brief #776 add the health issue (answers 4 and 5) and the conductor's switch to `Assign:` lines
   (answer 1's `plan` naming slots, and this repository's own `builder_start = "assign"`). This build changes no
   behaviour while `builder_start` is `start`, and this repository stays on `start`.

## Consequences

- A slot run needs no session to start it and no person to carry a message: the schedule starts it, the lease decides
  whether it lives, and GitHub says what it does.
- A slot has one open pull request (session rule 3 unchanged), so an `Assign:` of a new brief waits while it has one.
- `Pool: stop` holds while the comment exists; deleting it resumes the pool.

## Residual

- 2026-12-31: two takes in the same moment are settled by the read-back, which narrows the race and does not close it
  (GitHub has no compare-and-swap for a comment); the loser's extra marker stays and never counts. A pool in which two
  live runs share a slot would still be visible as two sessions posting under one name.
- 2026-12-31: a slot's marker counts only by an account in `verdict_authors`; a slot run under another account fails
  its read-back and exits 3 until that account is listed. Whether a builder account should be listed is the owner's.
- 2026-12-31: a slot run that dies holds its slot until the lease expires, at most 50 minutes; answer 4's schedule
  replaces it after that, so the brief's 15-minute goal needs the release or a shorter lease (Q-776-3).

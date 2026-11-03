# ADR-0262: Add REQ-047: A builder hands heavy runs to a first-in-first-out queue and keeps developing

- Status: Proposed
- Date: 2026-11-03
- Deciders: maintainers
- Related: SPEC-0040, ADR-0191, ADR-0223, ADR-0231, ADR-0254, REQ-040
- Requirements: REQ-047

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-03:

> A builder hands each heavy run (proof, the full suite, e2e, Compose stacks) to a first-in-first-out queue that one runner works through, and goes on writing code and tests while it waits, so on a low-memory machine development never stalls behind the heavy lock.

The brief is issue #520; the conductor reserved REQ-047, SPEC-0040 and this ADR number for it
(the field note on #520). The owner's direction of 2026-11-03, quoted as data, is recorded as one
row of `docs/runs/decisions-log.md`: "on low memory machines, waiting for 2 builders are time
taking on heavy locks, it is really killing hours and hours time and slow. Why can't we prioritize
development works when heavy runs are planned, at least we can move progress on development side.
Heavylock queue can operate FIFO." The owner's ruling on the order, the same day, quoted as data
and recorded as a second row: "one run at a time (or as many as your lock slots allow) - this is
the right strategy. I agree FIFO or Priority based queuing to unblock the development is great
strategy here."

Today the heavy-step lock (`scripts/agk/lock.py`: ADR-0191, slots and priority order in ADR-0231,
the lock token in ADR-0254) is a wait, not a queue: `lock.py run --name heavy` blocks its caller
until a slot is free. In the pilot of 2026-11-02 and 2026-11-03, with room for one or two builders,
the builders spent most of the day blocked while another builder's 20-minute suite ran, each
holding a session and its memory while doing nothing.

## Decision

1. REQ-047 is added to `docs/requirements.md` as `planned`, with nine criteria each testable
   with fake runs and a temporary queue folder. SPEC-0040 is added as `Draft`. Merging this pull
   request approves the requirement as a proposal; it does not approve the spec, which stays
   `Draft` until the owner's own `Approve:` line approves it.
2. The queue is off by default: `queue = true` in a new `[locks]` table of `agk.toml` turns it on,
   and with it off every command does exactly what it does today (SPEC-0040 rule 1). With it on,
   `lock.py submit` writes a job and returns at once, one `lock.py runner` works the jobs in the order
   that `[locks] queue_order` sets (`"fifo"`, the default: submission order; `"priority"`: the
   brief's `Priority:` first, an unreadable one last and never 0, then submission order, with a job
   waiting longer than `queue_max_wait` minutes, 120 by default, moving ahead of newer ones), one
   job or `lock_slots` jobs at a time and never pre-empting a running one, under the existing lock
   and slot rules, each on a detached worktree of its
   exact head, and `lock.py status` shows the queue with an estimated start from past durations
   (rules 2 to 8). Duplicates are one job and a newer head of the same branch replaces a waiting
   job in place; a dead, stale or crashed job is failed and never passed (rules 5 and 14).
3. No gate is skipped, weakened or reordered: only a passed result for the exact head is evidence,
   CI still runs every required check, and the workflows, `check_pr_body.py` and `evidence.py` do
   not change (rules 10 and 15). A builder queues and keeps developing, or ends with a `Report:`
   naming its ticket and is resumed through the existing stalled-pull-request path; the plan counts
   a builder that only waits as not building and offers its slot to development only when memory
   allows (rules 11 to 13).
4. The builds (a) to (f) of SPEC-0040 rule 16 will change these protected path classes:
   `scripts/agk/` (`heavy_queue.py`, new and installed, `lock.py`, `common.py`, `prepush.py`,
   `proof.py`, `session.py` and `session_plan.py`), `config/` (`config/session-rules.md`: one new
   builder rule and one sentence each in session rules 30 and 31), `kit/` (`kit/manifest.json`,
   `kit/templates/agk.toml` and `kit/templates/agk.adopt.toml`, a commented `[locks]` table),
   `agk.toml` (the same commented table; this repository keeps the queue off) and `tests/kit/`
   (their tests). Build (f) changes only guides, which are not protected. Each build adds its own
   ADR naming the classes it changes and citing this one, because the protected-path check counts
   only an ADR added or changed in the same pull request (`Q-S0040-14`). No build changes
   `.github/`, `constitution/`, `CLAUDE.md`, `Makefile`, `pyproject.toml`, `agk.mk`, `skills/`,
   `.claude/`, `.claude-plugin/` or `tests/kit_dev/`.
5. Brief #505 is closed as completed, so no build declares it; each build that changes `lock.py`,
   `prepush.py` or `proof.py` declares `Depends-on: #508` while brief #508 is open
   (`Q-S0040-13`). This pull request changes documents only and declares no dependence.

## Consequences

The requirement is listed as planned, and the spec and this ADR wait for the owner's approval.
Nothing is delivered until the builds merge. No check, flow or setting changes in this pull
request, and a project that does not set `[locks] queue = true` sees no change from any build.

## Residual

None. The intake checks cannot tell whether strict first in, first out, the replace-in-place rule
or the estimate are the right ones; that is the review of this pull request and the owner's
rulings on `Q-S0040-1` to `Q-S0040-18` (`Q-S0040-2` is ruled).

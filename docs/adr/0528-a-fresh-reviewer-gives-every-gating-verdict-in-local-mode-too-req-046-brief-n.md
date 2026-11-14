# ADR-0528: A fresh reviewer gives every gating verdict, in local mode too (REQ-046)

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0430, ADR-0431, ADR-0432, ADR-0444, ADR-0298, ADR-0525, Q-1013-1, Q-1013-3, brief #1248, plan #661
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `tests/kit/`, `.claude/`, `agk.toml`

## Context

ADR-0430 (Accepted) moved the gating verdict to a fresh reviewer session that reads only the bundle; ADR-0431 and
ADR-0432 built the reviewer slots, `review_bundle.py`, the `Review:` line and the shadow sample, and ADR-0444 let the
review guard write the verdict file in its scratch folder. Three things still kept the reviewer off the gate on
2026-11-14: `[flow] reviewer_slots` was never built (Q-1013-1); the guard refused the redirect that saves the bundle
(Q-1013-3); and local mode had no way to start a reviewer, so every verdict there was the conductor's, with the whole
planning context. Brief #1248 answers all three; no Accepted ADR covers these protected classes for this change, so the
build writes its own (session rule 36), with the brief's `Reserved:` number.

## Decision

1. `[flow] reviewer_slots` is a whole number, 0 by default; another value is refused naming the setting. 0 keeps
   today's behaviour everywhere. With 1 or more, the slots `r1` to `r<count>` are the gate: `session.py slot` runs them
   whatever `builder_start` says and refuses a name past the count; `conductor.py review` asks them; `checklist.py`
   point 2 prints `reviewer slots alive <n> of <count> (reviewer_slots)`; and `doctor.py` fails `reviewer-slots`
   (severity `error`) when `experimental_reviewer = true` is not set too, since the `architect-review` agent is
   installed only then (the co-owner's note on the brief, 2026-11-14).
2. The wait is `[flow] review_minutes`, a whole number 1 or more; unset, `[capacity] review_minutes` as the plan reads
   it, else 15. With slots counted, `conductor.py check-verdict --pr N` (and so the conductor's guard, which runs the
   same `full_problem`) accepts a verdict on the head only when it carries the slot's marker lines `agent:
   architect-review`, `tier: strongest` and `session: r<k>` (k within the count) and does not end `(conductor
   fallback)`, or when it ends `(conductor fallback)` and the newest `Review: r<k> #<n> <head>` line by a listed verdict
   author on the conductor issue is at least `review_minutes` old with no reviewer verdict. A fallback with no
   `Review:` line, or while the reviewer still has the head, is refused naming the setting.
3. `conductor.py review --pr N [--start]` prints one line: `review: off` (no slots), `... has its verdict`, `... with
   r<k> since <time>; the conductor gives no verdict until <time>`, `... fallback ...` (past `review_minutes`), `no
   reviewer slot is free` (each slot has a younger `Review:` line on a head with no verdict), or, for a head nobody has
   asked yet, `review: ask Review: r<k> #<n> <head>` for the conductor to post. With `--start` and both `auto_start` and
   `launch_adapter` set in the checkout and on the default branch, not paused and above `[flow] min_free_memory_mb`, it
   posts that line itself and calls the adapter once, as `launch.py` does, with `AGK_SESSION=r<k>`, `AGK_ROLE=reviewer`,
   `AGK_AGENT=architect-review`, `AGK_TIER=strongest`, `AGK_PR` and `AGK_SHA`, no brief, and a prompt naming only the
   slot, the pull request and the head; the session builds the bundle, posts its verdict, runs `slot --release r<k>` and
   exits. The `Review:` line is the slot's hold in local mode: the conductor takes no lease for it, because the adapter
   starts the session in its own worktree. The conductor's guard allows `review --pr <n>` and, only with the adapter
   configured as for `launch.py --adapter`, `review --pr <n> --start`.
4. `architect_guard.py --review` also allows exactly `python3 scripts/agk/review_bundle.py --pr <n> --sha <40-hex>
   [--base <ref>] > <file>`, one `>` to a regular file of a review scratch folder (`agk-review-<name>` in the user's temp
   folder, never in the checkout); every other redirect, write and command stays refused. With ADR-0444's verdict file
   and `check-verdict` step this settles Q-1013-3.
5. `.claude/agents/architect-review.md` names the scratch folder, the marker lines and the local start.
6. `agk.toml`'s `[[testing.map]]` entries of `scripts/agk/session.py` and `scripts/agk/conductor.py` list
   `tests/kit/test_reviewer_slots_local.py` (the map rule of `test_always_full_infra.py`).
7. `config.TABLE_KEYS["flow"]` (ADR-0527) lists `reviewer_slots` and `review_minutes`, so `doctor.py`'s
   `misplaced-settings` never reports them in `[flow]`; `review_minutes` is at home in `[flow]` and `[capacity]` alike
   (`scripts/agk/config.py`, outside the brief's `Touches:`, changed for the merge with brief #1245 by the correction on
   18d45a3).

## Consequences

- In local mode with `reviewer_slots = 1`, a fresh session reviews each ready head and the conductor's verdict is only
  the fallback; with 0, nothing changes.
- A verdict's marker lines are written by the session itself, from one account: the check proves their presence, not
  their truth (ADR-0430 residual).
- A reviewer session costs one adapter start and its memory per head; the floor holds starts back as it does builders.

## Residual

- 2026-11-30: in CI mode the reviewer slots are scheduled tasks (ADR-0431); nothing here schedules them, and the
  conductor's role file does not yet say to run `conductor.py review` before a verdict (outside the brief's `Touches:`,
  Q-1248-2).
- 2026-12-31: "the bundle only" stays a written rule; the runtime can read the checkout (ADR-0430 residual).

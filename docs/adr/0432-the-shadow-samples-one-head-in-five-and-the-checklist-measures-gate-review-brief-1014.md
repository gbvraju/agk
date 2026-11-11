# ADR-0432: The shadow samples one head in five and the checklist measures gate review (REQ-054)

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: ADR-0430, ADR-0431, ADR-0374, ADR-0420, SPEC-0023, SPEC-0035, amendment 160, brief #1012, brief #1013, brief #1014, plan #661
- Requirements: REQ-054, REQ-046

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

ADR-0430 decides that a fresh reviewer gives the gating verdict, that the shadow samples those verdicts and that the
nine-point checklist measures the gate (amendment 160 items 5, 6 and 8). ADR-0431 (brief #1013, build (a)) built the
reviewer slots, the `Review:` line and the `(conductor fallback)` ending. Brief #1014 is build (b): the shadow's sample, the
catch rate and the measures. No Accepted ADR covers these protected classes, so the build writes its own (session rule
36); 0432 is the brief's `Reserved:` number.

## Decision

1. `session.py` samples a head for the shadow when the integer value of the first 8 hex characters of its sha, modulo 5,
   is 0 (`shadow_sampled`); the same sha always gives the same answer, and a sha shorter than 8 characters is never
   sampled. The divisor is the fixed 5 of brief #1014 answer 1, not a setting.
2. The conductor posts `Shadow: s-shadow #<pr> <40-hex>` on the one open `agk-conductor` issue for a sampled head. The
   shadow slot is named `s-shadow`; `slot --take|--renew|--release s-shadow` use the builder slots' lease (ADR-0362,
   ADR-0425), and `slot --next s-shadow` prints `shadow pr #<n> <sha>` for the newest such line by a listed verdict author
   whose head is sampled and that no `Shadow: #<n> <sha> cleared|fix list|rejected` comment on the one open `agk-shadow`
   issue answers yet, `wait` otherwise, and `stop` on `Pool: stop` by an approver. It reads only those two issues, never a
   pull request's comments, so it never reads a `Verdict:` line. `.claude/agents/shadow.md` keeps its blind rules and is
   not changed: it stands at its word budget (`rules.py`, baseline 1280), and this decision is where the slot is
   described until a guide carries it (Q-1014-1).
3. `checklist.py` adds, each printed `unknown` when it cannot be measured and never 0:
   - point 5: review latency, from a head's `Report: <head> ready ...` to the first gating `Verdict:` by a listed verdict
     author that names that head, as the median and the worst in minutes; fix-list rounds per merged pull request (its
     `fix` verdicts); red mains whose cause is a cleared head (a failed push run on a pull request's base branch whose
     previous run of the same workflow there did not fail, laid to the latest merge before it, counted when that pull
     request's head was cleared); and the reviewer's catch rate of decision 4;
   - point 9: tokens per review, the mean of the `Usage: <n> tokens` figures of the gating verdicts that are not
     `(conductor fallback)`;
   - point 2: the reviewer slots alive (an `r<N>` lease marker on the conductor issue whose time is within
     `slot_seen_minutes`, 90 by default) and the share of gating verdicts whose first line ends `(conductor fallback)`.
   The yes, partly and no of each point are unchanged: the new measures add no threshold.
4. The catch rate comes from the `Marks:` comments (SPEC-0035 rules 3 and 4, amendment 160 item 6): `R` (and `C`, read as
   `R`) findings marked `right` or `both`, over those plus the `S` findings marked `right`. A head counts in the reviewer's
   rate or, when its verdict ends `(conductor fallback)`, in a separate fallback rate, never added together. It is
   printed `unknown` until 10 sampled heads (a `Shadow: #<pr> <sha> ...` comment) have a `Marks:` comment on their pull
   request, and `none` with no right finding. `checklist.py` holds the one reader (`marks_rate`), and the kit-only
   `shadow_count.py --marks FILE` prints the same figures from a saved comment list.
5. `metrics.py --save-checklist` saves, beside the fields it saves today, each run's `head_branch` and `event`, from the
   same GET. The reviewer slots' markers need no new field: the saved comments are listed by their update time
   (`since=`), and a marker's first line carries its own time.

## Consequences

- The owner sees whether gate review is faster (latency), cheaper (tokens) and right (rounds, red mains, catch rate),
  and how often the conductor still gives the verdict.
- A shadow slot can be scheduled (operations, after merge) and reviews one head in five, blind.
- A saved file written before this change has no `head_branch`; its red-main count reads `unknown`.

## Residual

- 2026-11-30: the shadow's guard (`conductor_guard.py --shadow`) allows no `session.py` command, so a shadow slot run
  cannot run `slot --next s-shadow` under it; `.claude/hooks/` is outside brief #1014's `Touches:` (Q-1014-1).
- 2026-11-30: the conductor's role file and its guard do not yet say or allow posting `Shadow: s-shadow ...` on the
  conductor issue; they are outside the brief's `Touches:` (Q-1014-1).
- 2026-11-30: the measures read the saved window only (7 days by default), so the catch rate needs 10 marked sampled heads
  inside one window; the cause of a red main is laid by time, not by the merge commit's sha, which the saved pull
  requests do not carry (Q-1014-2).
- 2026-12-31: no check tells a mark by a finding's own reviewer from another's while all sessions post from one account
  (SPEC-0035 rule 3, ADR-0430 residual).

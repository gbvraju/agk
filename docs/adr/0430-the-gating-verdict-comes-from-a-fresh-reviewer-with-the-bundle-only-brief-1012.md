# ADR-0430: The gating verdict comes from a fresh reviewer session that reads the bundle only

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: SPEC-0023, SPEC-0035, SPEC-0034, SPEC-0045, amendment 160, brief #1012, brief #1013, brief #1014, plan #661
- Requirements: REQ-046, REQ-054

## Context

On 2026-11-10 every gating verdict came from the conductor's run, the same long session that files briefs, answers
questions and posts `Assign:` lines, so each review carries the whole run's context and happens only while that run is
live; #965 waited 81 minutes for a verdict, and 6 red default branches followed cleared heads (brief #1012). The kit
already has a read-only review agent (`architect-review`, SPEC-0023 rules 1 and 2), a deterministic review document
(`review_context.py`) and a blind shadow (SPEC-0035), but none of them is at the gate, and the shadow has never posted
(#219: 0 comments). The owner asked for a new milestone that adopts the reviewer-without-the-conversation idea of the
Elephant-Goldfish Model `(verify: its licence and repository as the brief gives them)` without touching waves 1 to 4.

## Decision

1. A gating verdict (`cleared`, `fix list`, and `rejected`) comes from a review session started for that one head: the
   `architect-review` agent, on the `strongest` tier, holding a reviewer slot `r<N>`, that pushed nothing to the branch
   and is not the conductor's run (amendment 160 item 1).
2. That session reads only the goldfish bundle: the review document for the head, the brief's body, the ruling lines on
   the brief and the pull request, and the head's checks; its `Read:` line lists them (item 2).
3. The conductor posts `Review: <rN> #<pr> <head>` on the `agk-conductor` issue, answers, assigns and merges as today, and
   gives a verdict only as `(conductor fallback)` while no reviewer slot is alive (item 3).
4. Reviewer slots are counted by `[flow] reviewer_slots`, default `0`, which keeps today's behaviour (item 4).
5. The shadow audits one gating verdict in `[flow] shadow_sample` (default 5), chosen by the head's sha, blind as today,
   and never gates; marks name the reviewer `R` (items 5 and 6).
6. Local and personal modes start a new session with the bundle only, or say so and leave the review to a person (item 7).
7. `checklist.py` gains review latency, fix-list rounds and red mains after a cleared head (point 5), tokens per review
   (point 9), and slots alive and the conductor's share of verdicts (point 2) (item 8).

## Consequences

Reviews no longer wait for the conductor's hourly run, and the gate's judgment no longer depends on the planning
context; the conductor keeps routing and merging, so SPEC-0039 is unchanged. The cost is one more scheduled task per
reviewer slot and a review session per head, measured by item 8. This pull request changes documents only; briefs #1013
and #1014 build it, each with its own ADR naming the protected classes it changes, after the owner's
`Approve: <head> SPEC-0023` and `Approve: <head> SPEC-0035`.

## Residual

- 2026-11-10: all sessions post from one account, so the separation of decision 1 rests on the reviewer slot's marker
  lines (`agent:`, `tier:`, `session:`, written by the review session itself), the branch's `Claude-Session:` trailers
  and role files, not on identities; the helper checks those lines are present and consistent, not that they are true
  (due 2026-12-31).
- 2026-11-10: "the bundle only" is a written rule; the runtime can read the checkout, and no guard can tell a bundle read
  from another (due 2026-12-31).
- 2026-11-10: the number of slots, the sample rate and the fallback rule are the owner's (`Q-S0023-1` to `Q-S0023-3`)
  (due 2026-11-30).

# ADR-0453: A stopped builder hands over with one line and its pull request is labelled agk:handover

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: brief #1071, plan #661, amendment 162, amendment 150, ADR-0385, ADR-0442
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Builders stop in three ways: at the six-hour end of the builder prompt, by handing a pull request to a second builder,
and with no comment. On 2026-11-11 `Report: a990f50124d6 handing over` on #1045 and `Report: 645bfc0 handing over` on
#1041 left both pull requests in `agk:fix`, and nothing restarted a builder for hours: `route.py` `BUILT` reads only
`ready for review`, `fix list applied` and `merge of main`, and no state says that a pull request's builder is gone.
Only the launcher's 45-minute `STALL`/`SILENT` rules catch a silent end. The owner's word, 2026-11-12 09:29 to 09:31
IST: standardise the stopping comment and trigger the label; no 15-minute schedule; "File it".

## Decision

1. Amendment 162 to SPEC-0032 rules 2 and 3, applied to the spec text in the same pull request, as the brief asks.
2. A stopping builder's last comment has the first line `Report: <head> handing over: <reason>`, the reason one of
   `six hours`, `to <session>`, `blocked: <what>` or `done`. `route.handover_reason` reads it with one pattern; no
   reason reads as `six hours`; the older successor form with no colon reads as `to <session>`.
3. `route.state_of` computes the state of amendment 150 (`base_state`) and replaces it with a twelfth state,
   `agk:handover` (actor `launcher`, colour `f9d0c4`), only when that state is the builder's (`agk:build`, `agk:ci-red`,
   `agk:conflict`, `agk:fix`) and `handed_over` finds the newest `Report:` by the pull request's author or a listed
   verdict author to be a handing-over line whose reason needs a new builder, with no later comment by those authors but
   a `Verdict:`, `Answer:` or `Correction:` and no later push. An owner's state is never replaced.
4. `session.py queue --role builder` lists `agk:handover` first; `conductor.py sweep` prints `HANDOVER #<pr> <minutes>m`
   for each pull request with the label, from the label the router set (one reader, amendment 150 item 3).
5. `uninstall.py` removes the new label with the others, and the `ok` doctor fixture holds it, so the doctor's
   `state-labels` row and the uninstall list stay the router's own.

## Consequences

The launcher can restart a builder from one label filter or one `queue` line, on the router's next event, with no
schedule and no person. In a project whose repository has no `agk:handover` label yet, `doctor.py` `state-labels`
lists it until the router first sets it or a person creates it, as for any new state. The builder and launcher prompts
are scheduled tasks outside this repository; the co-owner changes them (builders end with the standard line; the
launcher restarts a builder for each `agk:handover` pull request). No workflow changes.

## Residual

- 2026-11-12: a silent end (no comment) still waits for the launcher's `STALL`/`SILENT` rules; this decision covers a
  builder that says it stops (due 2026-12-31).
- 2026-11-12: one account posts both the builder's and the conductor's comments, so only the first line tells a
  builder's comment from a `Verdict:`, `Answer:` or `Correction:` (lane F, due 2026-12-31).

# ADR-0646: An owner's answer is never missed by a park (REQ-066)

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: brief #1534, ADR-0543 (brief #1282), ADR-0559, SPEC-0059 rule 10, SPEC-0064 rule 2, #1532, #1519, #1511, #1516
- Requirements: REQ-066

Protected classes: `scripts/agk/`

## Context

On #1532 the owner's `Maintainer answer: accept` of 03:46:20Z was missed by the park of 03:46:21Z: `session.py watch`
read the comments once, decided to park on that read and wrote the label and the `Parked-by:` comment without reading
again. `owner_step` then counted only an answer newer than the `Parked-by:` comment, so only a second answer could unpark,
and that came 20 minutes later from the conductor's sweep, which the supervisor skips while a job runs. The same
functions unparked `wait Q-1518-1` on `Answer: Q-1518-2` (#1519) and keyed an `Owner needed:` by a Q id the owner had
already answered (#1511, #1516). SPEC-0059 rule 10 and SPEC-0064 rule 2 already promise an unpark on the owner's answer,
whoever sees it first; the code missed it. Options weighed (the brief): (A) re-read before the park only; (B) decide
parked and unparked from the owner item on a fresh read; (C) the router unparks on the answer's own run; (D) the
supervisor runs the owner step while a job runs; (E) the supervisor merges by itself; (F) one more conductor job per
answer.

## Decision

(B), (C) and (D) are chosen; (A) alone is not enough, (E) waits for the owner (Q-1534-5) and (F) is not chosen.

1. `session.owner_apply` is the one owner-wait write of every caller (`watch`, `conductor.py sweep`, `steward_owner.py`
   `park` and `relay`, the router and the supervisor). It decides on a fresh read (`session.owner_read`: the pull request
   and every comment page, never the run's memo, the pass's unchanged set or the page store), then writes. A caller's own
   read only says whether a step may be due. After a park it reads once more and unparks in the same call when an answer
   now closes the item.
2. A park of this rule (`own_park`) ends when no open owner item has the key it parked for, read over every comment: an
   answer before the park ends it, an answer to another Q id does not. No label but an open `Parked-by:` of this rule gets
   one repair `Unparked-by:`. A DELETE answered 404 counts as removed. A person's own `agk:parked` is never touched.
3. An `Owner needed:` is keyed by its Q id only while that question is open, else `owner-needed`. A
   `Maintainer answer: Q-<id>` closes that id only; `Maintainer answer: accept <sha>` closes the items only when the sha
   is the current head (Q-1534-2); any other `Maintainer answer:` or `Approve:` closes them all, as before.
4. `route.py` runs the unpark half (`unpark_only`) on a created comment whose first line is `Maintainer answer:`,
   `Answer:`, `Approve:` or `Correction:`, before it reads the label, with the workflow's own token (Q-1534-1). It never
   parks.
5. `conductor.py watchdog --pass`, while a job still runs, runs `owner_pass`: after `change_reads` says something changed
   and `refused_here` allows it, `owner_apply` on each open pull request labelled `agk:parked`, `agk:question`,
   `agk:approve` or `agk:owner-merge`. It moves no read mark. The cadence stays `[autopilot] interval_minutes`; no
   one-minute entry is added (the owner's direction: event first).

## Consequences

An answer posted between a caller's read and its write leaves no label and needs no second answer, in every mode. In
hosted and local mode the router's run on the answer unparks within seconds; the supervisor's next pass is the safety
net. Personal mode parks nothing, as before. Two writers converge on one label state; a race can leave one extra
`Unparked-by:`, and readers take the newest. The merge after an unpark still comes from the conductor's job and
`merge_cleared.py` with every hold.

## Residual

- 2026-11-19: `Answer:` is not yet in `.github/workflows/agk-route.yml`'s trigger, so a steward's evidence answer
  unparks at the supervisor's pass or the sweep; the one-line workflow change is the owner's (Q-1534-4).
- 2026-11-19: the router's `asks_owner` keeps its own answerers (spec approvers), so the label it writes is unchanged;
  sharing one reader with `session.open_owner_items` waits for a ruling (Q-1534-8).

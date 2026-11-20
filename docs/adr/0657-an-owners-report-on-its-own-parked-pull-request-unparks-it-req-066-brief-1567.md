# ADR-0657: An owner's Report on its own parked pull request unparks it (REQ-066)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1567, brief #1282 (ADR-0543), brief #1534 (ADR-0646), brief #1568 (ADR-0658), SPEC-0059 rules 1 and 10
- Requirements: REQ-066

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The owner wait (ADR-0543, ADR-0646) parks a pull request whose `Owner needed:` stays unanswered, and unparks it only on
an `Answer:`, `Maintainer answer:`, `Approve:` or `Correction:`. On 2026-11-20 the owner's own hand change #1561 was
parked at 02:12Z (`Parked-by: wait owner-needed`) after the conductor asked him for a body line and his merge command; he
did the work and posted `Report: 09509d30... ready for review` at 02:55Z, and nothing unparked it for 37 minutes, until a
`Maintainer answer: accept` at 03:32Z. Replaying #1561's comments on main confirms it: `owner_step` gives no unpark. A
`Report:` never closed the item, and the router's unpark run started only on an answer. Sessions and the owner post as
one login (SPEC-0059 rule 1, Q-S0059-4), so a `Report:` by that login cannot show by itself that the owner posted it.

## Decision

1. `session.open_owner_items` takes `own`. With it, a ready report (`READY_REPORT`, the forms of `READY_REPORTS`) by the
   pull request's author that names the current head closes an `owner-needed` item posted before it. It never closes a Q
   id question, and an older head, `Report: <sha> handing over`, another login or a report posted before the ask
   closes nothing.
2. `session.owner_own` decides `own` with GET reads only, and only when a report could change the step. One case: the
   body has a `Flow: owner change` line and no live `taken:` (`live_takes`) that still counts names its brief. The
   other: the author is a spec approver and no `taken:` ever named its brief. By the maintainer answer to Q-1567-1
   (2026-11-20), a take no longer counts for the first case when it is older than the newest `Owner needed:` of a
   listed verdict author on the pull request. It also stops counting when a `Report: <sha> handing over` follows it,
   on the brief or the pull request, before the next take: each hand-over ends the newest take before it. The second
   case keeps "no take ever": under one login it is what keeps a builder's pull request from unparking on its own
   report. A builder's `Flow: builder ...` line is no hand change, even when it says "by hand". An unreadable brief
   is not the owner's.
3. `session.owner_apply` stays the one write. The unpark it writes on a report removes the label and posts one
   `Unparked-by: report <sha12>`. `UNPARKED_BY` reads both forms, so the park is over. `unparked_owed` counts only
   `Unparked-by: answer`, so `next` offers no builder the owner's own pull request; it goes to review.
4. The router's comment run also unparks on a ready `Report:` on a pull request labelled `agk:parked`
   (`route.owner_report_event`), before the label is read, so it routes to review in the same run. The conductor's
   sweep and its owner pass go through the same `owner_apply`.

Settings: `[flow] owner_wait_minutes` is unchanged and still refused naming the setting; a park in `owner_rest_hours`
at `owner_utc_offset` unparks on the report the same way. `review_mode` solo: the person's `Confirmed:` stays the
verdict; the unpark only returns the pull request to review. `pr_mode`: no change to slots. `execution` hosted: the
router unparks on the comment; local: the conductor's pass does. `[personal] forge = "files"`: nothing is parked and
nothing changes. A person's own `agk:parked` (no `Parked-by:` of the rule) is never removed.

## Consequences

The owner's report on his own parked hand change unparks it and puts it in review, with no extra answer. A builder's
report never ends a park. The router reads the pull request and its comments again on a ready report only when the
pull request is labelled `agk:parked`. When the conductor's next pass sees a report that could close the wait, it reads
the brief's comments once.

## Residual

- 2026-11-20: Q-1567-1 is answered (09:20Z). Before the answer, #1561 itself stayed parked: brief #1536 carries three
  `taken:` lines with no `released:` (cb1458r, cb1546, cb1536), and #1561's open `Brief: #1536` keeps them live. All
  three are older than #1561's `Owner needed:`, so the replay of its comments now unparks at the report.

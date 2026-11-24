# ADR-0788: An evidence Answer: closes a maintainers question in the router's label (REQ-066)

- Status: Accepted
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1901, SPEC-0059 rules 3, 4 and 10, ADR-0442 (the maintainers question in the label), ADR-0497 (a new head
  closes it), ADR-0646 (`Answer:` in the owner wait), ADR-0685, ADR-0722, ADR-0723 and ADR-0725 (the other closers, unchanged)
- Requirements: REQ-066

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

On #1897 a builder posted `Question: Q-1891-1 for the maintainers` at 05:13:18Z and the conductor answered
`Answer: Q-1891-1: (b)` from evidence at 05:14:40Z. `session.open_owner_items` closed the owner wait's item on that
answer, but `route.owner_ask` cleared its one `question_open` flag only on a `Maintainer answer:` or `Approve:` by a spec
approver or on a newer head, so the label stayed `agk:question` (replayed on the comments up to 05:15:49Z: `agk:question`).
SPEC-0059 rule 10 says an evidence answer "ends the wait at once". The owner's word (2026-11-24, the steward chat, quoted as
data): "Yes, file the evidence-answer label brief".

## Decision

1. `route.owner_ask` keeps each open maintainers question by its Q id (`session.QUESTION_ID`, else the key `question`, as
   the owner wait keys it). A question posted before the head's last push opens nothing, as before.
2. A later comment whose first line is `Answer: Q-<id>` (`session.ANSWER_LINE`, imported) by an answerer, the listed
   verdict authors and the spec approvers as `session.owner_people` reads them, closes that question only. Another id,
   an earlier answer or another login closes nothing; with two questions open the label stays for the other.
3. It closes no `Owner needed:`, approval ask or merge ask (`Q-1901-1`, conservative). A `Maintainer answer:` or `Approve:`
   by a spec approver still closes every open question, as before. No new setting and no new refusal.

## Consequences

A settled question frees its pull request at once. A test runs the question fixtures through both readers and fails when one
reads a question open and the other closed.

## Residual

The two readers still differ where the brief keeps them apart: a newer head closes a question in the label only, and a
`Correction:` naming the id closes it in the owner wait only. Recorded 2026-11-24.

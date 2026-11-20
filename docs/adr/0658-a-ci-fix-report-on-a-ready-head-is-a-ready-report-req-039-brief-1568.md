# ADR-0658: A CI fix report on a ready head is a ready report (REQ-039)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1568, amendment 150 (the ready report of `route.py`), amendment 162, brief #842 (ADR-0384), ADR-0385
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The router labels a non-draft head with a `Brief:` line `agk:build` until a verdict names it or its author posts a ready
report, and `route.BUILT` read only `Report: <sha> ready for review|fix list applied|merge of main`. Builders also post
`Report: <sha> CI fix ...` after fixing a red check, and on 2026-11-20 two did: #1563 waited about 19 minutes in
`agk:build` (03:03Z to 03:22Z) until the same builder posted `ready for review`, and #1562 was labelled `agk:build` the
same way. The same three forms were written again, by hand, in `session_plan.WAITING_REPORT`, which the conductor's
review-queue reader and the `[flow]` capacity count use, and the builder prompt named only `ready for review`.

Options weighed: (A) refuse `CI fix` and tell builders to post `ready for review` (Q-1568-1); (B) read `CI fix` as one more
ready form, with every form in one list.

## Decision

(B) is chosen.

1. `READY_REPORTS = ("ready for review", "fix list applied", "merge of main", "CI fix")` is the one list of ready forms.
   It is defined in `scripts/agk/session.py`, not `route.py` as the brief has it: `route.py` and `session_plan.py` both
   import `session.py`, and `session_plan.py` cannot import `route.py` (`route.py` imports `merge_cleared.py`, which
   imports `session_plan.py`). `route.py` imports it by name, so `route.READY_REPORTS` is the same tuple.
2. `route.BUILT` (`session.READY_REPORT`) and `session_plan.WAITING_REPORT` are built from it, so a `Report: <sha> CI fix`
   by the pull request's author on the current head of a pull request that is not a draft is a ready report for the
   router, the conductor's review queue and the capacity count. The draft rule comes first, so on a draft it changes
   nothing; an old sha or another login is no ready report; the checks then decide the label as for `ready for review`.
3. The builder prompt (`session.py prompt`) keeps naming `ready for review` first and names the other forms from the
   tuple. Tests hold the three readers and the prompt to the tuple.

No setting is added. `execution` hosted labels on the comment (the router already starts on `Report:`), local in the
conductor's `route.py --all` pass; `review_mode`, `pr_mode` and `[flow] auto_merge` change only by the label;
`[personal] forge = "files"` has no labels and no change; the capacity rule is unchanged.

## Consequences

A fixed head enters review on its `CI fix` report instead of waiting for a second `Report:`; one more head may count as
waiting for a verdict sooner under `reviews_in_flight`. A new ready form is added in one place.

## Residual

- 2026-11-20: `caps.py` `READY` still measures to the first `ready for review` only (a time measure, not a label);
  not changed here.

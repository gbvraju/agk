# Proposed spec amendments 94 (SPEC-0025; REQ-039)

Date: 2026-10-29 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is applied by
ADR-0166, and it changes `docs/specs/0025-a-team-can-run-independent-pull-requests-in-parallel-without.md`. The conductor gave
the number 94 for this build on #297 (brief #282; verdict on 855c1af, Q-282-1).

1. **SPEC-0025 rule 5.** "A governance check fails while any named pull request is not merged, naming the rule and the number"
   becomes: "A governance check fails while a named number is neither a merged pull request nor an issue closed as completed
   (a brief whose merged pull request closed it), naming the rule, the number and which case it is: an open issue, an issue
   closed as not planned, an issue not closed as completed, or a pull request that is not merged." "The workflow fetches the
   state of each named pull request" becomes "the workflow fetches the state of each named number from the issues endpoint,
   which answers for a pull request and an issue alike".
2. **Tests (SPEC-0025 rule 11).** `tests/kit/test_pr_mode_briefs.py` (each case, the workflow's fetch and session rule 3). Its
   marker is `REQ-039`.

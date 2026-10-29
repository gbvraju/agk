# ADR-0166: a Depends-on line accepts a brief closed as completed (REQ-039, brief 282)

- Status: Accepted
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0086
- Requirements: REQ-039

Protected classes: `.github/`, `config/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #282 (priority 1). In a project pilot (2026-10-27) the briefs carry `Depends-on: #<brief>` lines between issues, as
`session.py` reads them. A builder copied its brief's `Depends-on: #29` into its pull request body. `check_pr_mode` read every
`Depends-on` as a pull request and failed with `rule 5: #29 is not merged`, although brief #29 was closed by its merged pull
request #49. The cause was reproduced first on this repository: the governance workflow fetched `pulls/$n`, which answers 404
for an issue, wrote the fallback record `{"number": 29, "merged": false}`, and the check printed `FAIL pr-mode: rule 5: #29 is
not merged`. The tests were written first (checkpoint 58a6d96), and 9 of them were red on the unchanged tree.

## Decision

1. **The check (answer 1).** `check_pr_mode.py` rule 5 accepts `#n` when its record is a merged pull request (as today) or an
   issue closed with the state reason `completed`. Every other case fails with its own message: `is an open issue`, `is an
   issue closed as not planned`, `is an issue not closed as completed` (a duplicate, or no reason), `is a pull request that is
   not merged`, and `is not merged` for a number with no record or a record that does not say whether it is a pull request
   (the workflow's fallback when a fetch fails, read as before). A record is an issue only when it says
   `pull_request: false`, so nothing is guessed. Strict mode (rule 6) is unchanged: any `Depends-on` line fails there.
2. **The workflow (answer 1).** The `PR states and open pull requests` step of `governance.yml` fetches
   `repos/<repo>/issues/<n>` with one GET a number. That endpoint answers for a pull request and for an issue alike, and its
   `pull_request.merged_at` tells a merged pull request. The record holds `number`, `pull_request`, `merged`, `state` and
   `state_reason`. The permissions are unchanged (`issues: read` was already granted). The fallback record on a failed fetch
   is unchanged.
3. **The rules (answer 2).** Session rule 3 (`config/session-rules.md`, shipped by the kit) now says that a pull request's
   `Depends-on: #n` names what must merge first, a pull request or a brief issue closed as completed by its merged pull
   request, and that a dependency already on the default branch needs no `Depends-on` line.
4. **Tests (answer 3).** `tests/kit/test_pr_mode_briefs.py`: the pilot's case passes; an open issue, an issue closed as not
   planned, one closed as a duplicate or with no reason, an unmerged pull request and a missing record each give their own
   message, also all in one run; strict mode still fails; the workflow reads the issues endpoint; the session rule says the
   new text. Flow mode: fragment `changelog.d/depends-on-brief.md`, no version bump. `kit/hashes.json` is not edited
   (session rule 14), although the brief's Touches names it.

## Spec amendments

Amendment 94 (`docs/runs/proposed-spec-amendments-94.md`) changes SPEC-0025 rule 5 (a named issue closed as completed is in, and
each failing case is named). The number was given in the verdict on 855c1af (Q-282-1).

## Consequences

- A builder can copy its brief's `Depends-on` line into its pull request without a false red once the brief is closed as
  completed.
- An issue closed as completed by hand, with no merged pull request, also passes: the check reads the state reason GitHub
  records, not which pull request closed the issue (that needs the timeline, one more fetch a number).

## Residual

- 2026-10-29: Q-282-1 and Q-282-2 were answered in the verdict on 855c1af. Q-282-1 named amendment 94. Q-282-2: the
  getting-started guide's `pr-mode fails` entry says the new rule, in this pull request.

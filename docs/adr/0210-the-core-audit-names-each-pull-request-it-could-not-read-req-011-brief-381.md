# ADR-0210: the core audit names each pull request it could not read (REQ-011, brief 381)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0188
- Requirements: REQ-011

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #381 (priority 2, split from #278): the core audit of ADR-0188, run on the default branch twice on 2026-10-30, reported
13 of its 23 governance checks as `cannot-check` because a few pull requests' check runs could not be read (5 on the first
run, 4 on the second), and did not say which. Nobody could tell whether a check truly never fired, and plan #278 must not
retire a check on a `cannot-check`. The tests were written first (`tests/kit/test_core_audit.py`, 16 failed, 36 passed at the
first checkpoint of the pull request).

## Decision

1. **The unread pages are named (answer 1).** The text report gains a section `Unread pages:` with one line `#<n> <page>`
   per pull request and page that could not be read in full, in number order, where `<page>` is `commits`, `check runs`,
   `job`, `combined step` (a failed run whose job shows only the one combined step of the early workflow) or `comments`.
   `--json` gains the same list under `pull_requests.unread`, as objects with `number` and `page`. A pull request with two
   unread pages has two entries, in that page order; a pull request with no governance run at all is `check runs`; a failed
   job with no failed step is `job`. With no unread page the section says `none`; when the list of pull requests itself
   cannot be read, no pull request can be named and the list is `cannot-check`.
2. **`--only N,N` (answer 2)** reads just the named pull requests, every other rule unchanged (the period of `--since`
   included). The list of pull requests stops at the lowest number named. A named number that is not in that list is a bad
   call (exit 2, naming the setting `--only`), never a quiet zero. It writes nothing except with `--write`.
3. **Nothing else changes (answer 3):** the counting rules, `at least N`, `cannot-check`, the never-fired list and the totals.

## Consequences

- A maintainer re-reads only the named pull requests with `--only` and can turn a `cannot-check` into a real count.
- A run with `--only` reports on those pull requests alone; its never-fired list covers only them.

## Residual

- None (2026-10-30).

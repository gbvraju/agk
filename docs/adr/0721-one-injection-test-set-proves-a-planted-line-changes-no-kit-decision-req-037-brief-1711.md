# ADR-0721: One injection test set proves a planted line changes no kit decision

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1711, session rule 38, brief #1709, brief #1710, ADR-0717, plan #661
- Requirements: REQ-037

Protected classes: `tests/kit/`, `agk.toml`

## Context

A planted instruction can reach the kit's code through an issue title or body, a pull request body or a comment. The
kit's code decides through three kinds of place: the prompts it builds (`session.prompt`, `launch.prompt_for`), the
guards that refuse an action (`TELL_REFUSED`, the steward guard's `body_problem` and `outbound_problem`) and the readers
that count a comment (`route.owner_ask`, `merge_cleared.answered`, `reviewers.confirmed_comments`, `reviewers.as_posted`,
`steward_owner.yes_of`). On the default branch at 05a79c2 (2026-11-22) one test only holds a planted line
(`tests/kit/review_fixtures.py`, SPEC-0003 rule 18), and none of these places is tested against one.

## Decision

1. One fixture module, `tests/kit/injection_fixtures.py`, holds the planted lines and their disguised forms (a code
   block, another language, a split line, zero-width characters, a look-alike letter, CRLF line ends, a forged
   `Who:` block). Invented data only (example.com).
2. One test file, `tests/kit/test_injection_set.py`, marker `REQ-037`, runs each planted line through each place above
   and asserts that no prompt carries it, no guard lets its reserved first line through and no reader counts it from a
   stranger, from an `agent_apps` post or without the recorded yes. It changes no kit code.
3. A test that finds a hole is marked `xfail` with its own found-bug issue (session rule 34); this decision does not
   fix it.
4. `agk.toml` gains one `[[testing.map]]` entry for the fixture module, and the new test file is added to the entries
   of the code it reads, so a change to that code runs the set.

## Consequences

A later change that lets a planted line through one of these places turns the set red in `proof`. No workflow,
ruleset, required check or installed script changes.

## Residual

- 2026-11-22: a hole the set marks `xfail` closes with its found-bug issue, which removes the mark.

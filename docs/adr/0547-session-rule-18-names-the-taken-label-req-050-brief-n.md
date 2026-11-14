# ADR-0547: Session rule 18 names the taken label that claim adds

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: brief #1276, brief #1251, ADR-0529, pull request #1261
- Requirements: REQ-050

Protected classes: `config/`, `tests/kit/`, `agk.toml`

## Context

Brief #1251 (pull request #1261, ADR-0529) made `session.py claim` add the label `agk:taken` to the brief it
takes, beside its one `taken:` comment, so the planner sees a taken brief without reading its comments. The
label is added on the same path for a brief and for a build (`claim --build X`). Session rule 18 of
`config/session-rules.md` still said that `claim` "posts one comment and nothing else". The owner kept the label
(Q-1251-2) and asked that the rule be updated (brief #1276).

## Decision

1. Session rule 18 says that `claim` "posts one comment and adds the label `agk:taken`, and nothing else", and
   that `claim --build X` "posts `taken: <id> <date> build (<x>)` and adds the label `agk:taken`". No other word
   of the rule changes.
2. `tests/kit/test_rule18_claim.py` reads `TAKEN_LABEL` and the body of `claim` in `scripts/agk/session.py` and
   checks that rule 18 names that label exactly when `claim` adds it, and that the `claim --build X` sentence
   names it exactly when a build's claim adds it too, so the rule and the code cannot drift apart again. It
   joins the test map of `scripts/agk/session.py` and of `config/session-rules.md` in `agk.toml`, and
   `tests/kit/test_session_rules.py` records rule 5's merged text as reworded the same way.
3. CI and local mode take a brief with the same `claim` and the same GitHub label. Personal mode files no
   issues, and nothing changes in it.

## Consequences

A session that reads rule 18 learns that a claim also changes the brief's labels, as the planner already relies
on. A later change that drops or renames the label, or guards it for builds, fails the new test until rule 18
follows.

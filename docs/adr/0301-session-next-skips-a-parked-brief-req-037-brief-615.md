# ADR-0301: `session.py next` skips a parked brief (REQ-037, brief 615)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0195
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #615 (pilot feedback #606 item 6): `next` offered a parked item to every builder. No Accepted ADR names this rule, so it is decided here. The number was reserved for brief #615.

## Decision

1. A brief is parked when it has the label `agk:parked` or a line starting `Parked:` in its body (`is_parked`).
2. `next` skips a parked brief with `skip #<n>: parked` (the reason `judge` returns, after `stale`) and offers the next free brief.
3. The label is created only when missing, by the router's `Labels.ensure` (one POST), which gains a colour and description for it. It is not in `route.LABELS`, so the router never removes it.
4. `session.py queue` is unchanged: it lists open pull requests by router label and never lists briefs, so there is nothing in it to mark (Q-615-1).

## Consequences

A parked brief is no longer taken by a builder; a person lifts it by removing the label or the line.

## Residual

Q-615-1: the brief asks that `queue` list a parked brief marked parked; `queue` lists no briefs. Left unchanged (the most conservative reading); a reviewer says whether a brief listing is wanted.

# ADR-0720: The merger reads the owner's association when the permission cannot be read (REQ-046)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0711, SPEC-0039, brief #1729, brief #1709, plan #661
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

ADR-0711 decision 3 holds a pull request as `outside author (rule 5)` when its author's permission, read with one GET
of `repos/{o}/{r}/collaborators/{login}/permission`, is not `write`, `maintain` or `admin`, and holds it the same way
when that answer cannot be read. A cloud session's GitHub proxy refuses that path with HTTP 403, so from a cloud
session `merge_cleared.py` held every pull request, the owner's own included, and with `execution = "local"` every
cleared head waited for the owner's `--owner` merge (brief #1729).

## Decision

1. ADR-0711 decision 3 is changed for one case only: when the permission read returns nothing, `outside_author`
   reads the pull request's own `author_association` from the payload it already has (no new call). Only `OWNER` is
   inside (`merge_cleared.INSIDE_ASSOCIATIONS`, Q-1729-1); `MEMBER`, `COLLABORATOR`, `CONTRIBUTOR`,
   `FIRST_TIME_CONTRIBUTOR`, `FIRST_TIMER`, `NONE`, any other value and a missing one stay outside, because only
   `OWNER` always carries the write bar the merger keeps.
2. A head repository other than the base, a deleted one or a missing author is outside before any read, as today.
   When the permission read answers, its `permission` decides, as today, whatever the association.
3. Nothing else changes: the trusted verdict authors, the fork hold and the owner-only `--owner` lift stay as
   ADR-0711 decides. `execution`, `[flow] auto_merge` and `conductor_accounts` are read as before.

## Consequences

From a cloud session the merger again merges the owner's own cleared changes. A collaborator's or member's pull
request still waits for the owner's `--owner` merge there, as the permission read would hold a read-only one.

## Residual

- 2026-11-22: a cloud session cannot tell a write collaborator from a read-only one, so their pull requests stay held
  for the owner there (Q-1729-1).

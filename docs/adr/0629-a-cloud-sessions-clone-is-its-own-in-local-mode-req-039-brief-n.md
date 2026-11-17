# ADR-0629: A cloud session's clone is its own in local mode

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: ADR-0551, brief #1482, brief #1471, Q-1471-1, Q-1301-1, plan #661
- Requirements: REQ-039

## Context

ADR-0551 decision 1 makes a clone shared by sessions when `execution = "local"`, a `[flow] launch_adapter` is set, or
another `agk-*` worktree exists, and exempts a cloud session (`CLAUDE_CODE_REMOTE=true` (verify)) from the adapter case
only. So with `execution = "local"`, `session.py claim` and `push-check` refused every cloud builder in its own clone's
main folder (measured by cb1471 on #1478; reproduced on main at cb9149e by this brief's tests). The owner ruled on
Q-1471-1 (a): the setting stays, and a cloud session's own clone is exempt from it, as it already is for the adapter.

## Decision

1. `common.clone_shared_by` counts `execution = "local"` only outside a cloud session: when `CLAUDE_CODE_REMOTE` is
   exactly `true`, local mode alone does not make the clone shared, exactly as the `launch_adapter` case reads it. This
   amends ADR-0551 decision 1 in that one point.
2. The `agk-*` worktree case is unchanged and still applies in a cloud session. On a machine local mode is refused in
   its main folder as before; the refusal text and the setting it names are unchanged. Hosted, hybrid, pool and
   personal mode are unchanged.

## Consequences

A cloud builder of a local-mode repository claims and pushes from its own clone. Protected path classes changed:
`scripts/agk/` (`common.py`), `tests/kit/` (`test_cloud_clone_local_mode.py`) and `agk.toml` (a `[[testing.map]]`
entry for `common.py`). No workflow, ruleset, required check, spec or secret changes.

## Residual

- 2026-11-17 (verify): that Claude Code on the web sets `CLAUDE_CODE_REMOTE=true` is carried over from ADR-0551, not
  re-read from its documentation; this session measured it set to `true`.

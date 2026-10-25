# ADR-0123: the red default branch brief, opened by the router and handed out alone by `next` (REQ-039 build d, SPEC-0032 rule 7)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0115, ADR-0118, ADR-0120
- Requirements: REQ-039

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0032 (Approved) rule 7 is build (d) of brief #179, assigned to this session by the conductor with this ADR number reserved. The tests were written first (`tests/kit/test_route_red.py`, `tests/kit/test_next_red.py`; on the unchanged tree most of them failed).

## Decision

1. **The router opens, updates and closes the brief** (an issue counts as its own only when its author is the job's token, `github-actions[bot]`, so a hand-written issue of the same shape neither stops work nor is touched; the verdict on the first head) (`route.py`): on a `push` to the default branch or a finished workflow run on it (and with `--branch`), it reads the checks and statuses of the default branch's head (the router's own check excluded). Pending: it does nothing. Red: it opens one issue `The default branch is red`, labelled `agk-brief` (the label is created when missing), whose body is a brief with `Priority: 0`, `Advances: none`, `Touches: **`, `Size: S` and the answers `Failing check`, `Head` and `Run`; it updates the open one when the failing check or the head changes and writes nothing when they do not. Green: it closes every open red-branch issue with `state_reason=completed`. It writes no comment and names no cause (Q-K4-288, Q-K4-290). An unreadable branch is a failure naming rule 7 and writes nothing; a read-only token skips (Q-K4-291).
2. **`session.py next`**: while an open issue is the red-branch brief (title `The default branch is red` and a `Priority: 0` line, not a pull request) it hands out only that brief: no other brief and no stalled pull request is offered. A session that cannot have it (another holds it, or it fails its shape) gets `default branch red` and exit 1 (Q-K4-289).
3. **The shape**: `brief_problems` accepts the pair `Advances: none` and `Priority: 0` together, and only together (amendment 60 for SPEC-0034 rule 2).
4. The workflow `agk-route.yml` keeps its triggers and its five permissions (`issues: write` is among them); only its comment changes.
5. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-bd.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. Amendment 60 (`docs/runs/proposed-spec-amendments-60.md`) is for the maintainers to apply to SPEC-0034.

## Consequences

- A red default branch stops new work: every session but the one on the brief is told so, and the brief closes itself when the branch is green. A pull request labelled `agk:ready` keeps its label, so a person may still merge the fix.
- The `Measured:` rule for a `Priority: 0` brief (build e of SPEC-0032, rule 9) must not fail the router's brief, which names no cause (Q-K4-288).

## Residual

- 2026-10-25: the router reads the checks of the branch's head at each event; a flaky check that goes red and green again opens and closes the brief each time (due 2026-12-31).
- 2026-10-25: `branch_state` counts every check run of the head except the router's, not only the required ones: reading the ruleset needs an admin token that the job does not have, so a failing optional check on the default branch also opens the brief (due 2026-12-31).

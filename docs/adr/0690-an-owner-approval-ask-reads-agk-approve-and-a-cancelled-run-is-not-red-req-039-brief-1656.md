# ADR-0690: An owner approval ask reads agk:approve, and a latest cancelled run is not red

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1656, ADR-0143 (decision 2 changes here), ADR-0471, ADR-0497, ADR-0442, the case of #1654
- Requirements: REQ-039

## Context

On #1654 the conductor's `Owner needed:` asked for `Maintainer answer: amendment 196 approved` and `... 197 approved`.
The router labelled the pull request `agk:question`, not `agk:approve`, since `base_state` returns `agk:question` for
any open owner ask and `agk:approve` comes only from a verdict's `Approval:` line. After the owner's answers the router
labelled it `agk:ci-red` with governance green: the only `proof` run that was not skipped had been cancelled, and
ADR-0143 decision 2 reads a latest cancelled run as red. The project runs `execution = "local"`. The tests were written
first (`tests/kit/test_route_latest.py`, `tests/kit/test_route_owner_ask.py`: 5 failed, 26 passed on the unchanged
tree).

## Decision

1. **The approval label** (`scripts/agk/route.py`, `owner_ask`). An open `Owner needed:` by a listed verdict author
   whose body names `Maintainer answer: amendment <n> approved` or `Approve: SPEC-<n>` gives `agk:approve`; any other
   open ask gives `agk:question`. An ask that names both an approval and a plain question gives `agk:approve`. The
   same owner answers close it as before (`asks_owner`, ADR-0497), and it stays right after `agk:parked`, before every
   builder state (ADR-0471).
2. **A latest cancelled run is not reported** (this replaces ADR-0143 decision 2 for labels). For the pull request
   label (`base_state`) and the state of the default branch (`branch_state`), `judged(..., cancelled_unreported=True)`
   leaves out a judged latest run whose conclusion is `cancelled`, and its name reads as not reported. In local mode
   the builder's evidence then decides (`local_proof`), as for a check that never ran; in hosted mode the head reads
   `agk:ci-running` until a new run reports. On the default branch (`wait` false) a cancelled run is not waited for and
   is not red. A newer failed run of the name, or any other conclusion of `FAILED_RUN`, stays red. With
   `required_checks` only a listed name is judged; without it every run counts, so a cancelled run of any name waits.
3. **What does not change.** `FAILED_RUN` keeps `cancelled`, and `judged` keeps it by default, so the callers that
   re-run or report a red check (`conductor.py`, `session.py`, `stalls.py`, `failing`) still see a cancelled run and
   the conductor's pass re-runs it as today (the recommendation of Q-1 of the brief). `review_mode`, `pr_mode` and
   personal mode (no labels) are unchanged.

Protected path classes changed: `scripts/agk/` (`route.py`), `tests/kit/` (`test_route_latest.py`,
`test_route_owner_ask.py`, and `test_route.py`, whose AC1 case read a cancelled run as red) and `docs/adr/` (this
file); `kit/hashes.json` is unchanged (`kit_hashes.py`: ok).

## Consequences

The owner's label filter shows a pull request that waits on an amendment or spec approval as `agk:approve`, and a head
whose only red run was cancelled no longer reads `agk:ci-red`: in local mode the builder's evidence decides, in hosted
mode it waits for the next run.

## Residual

- 2026-11-21: in hosted mode a cancelled run that nobody re-runs keeps the head `agk:ci-running`; the conductor's pass
  re-runs it, and `stalls.py` still lists it as red (due 2027-01-31).

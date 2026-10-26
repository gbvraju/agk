# ADR-0143: the router reads the latest run of each check (REQ-039, brief 229, SPEC-0032 rules 2 and 7)

- Status: Accepted
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0123, ADR-0137
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #229 (priority 1, measured on #226): the head of #226 held a cancelled `proof` run (stuck in GitHub's cleanup and cancelled), then a `proof` success, `governance` success and `agk-route` success. GitHub's required checks read the latest run of each name and were green; `route.py` read every check run of the head and set `agk:ci-red` because one of them was `cancelled`. Since #220 cancels superseded runs and gives a description edit its own run, a head holds an older run with a different result more often. The conductor assigned the brief to `builder-b` on #204 with this ADR number and amendment 79 reserved. The tests were written first (`tests/kit/test_route_latest.py`: 7 failed, 3 passed on the unchanged tree).

## Decision

1. **The latest run of each check** (`scripts/agk/route.py`, `latest_runs`): before it decides `agk:ci-running`, `agk:ci-red` or green, the router keeps for each check name only the run with the highest `id`, the later `started_at` breaking a tie. This applies to the label of a pull request (`decide`), to the state of the default branch (`branch_state`) and to the name and link of the failing check (`failing`).
2. **A latest run that is `cancelled` is still red**, and so is a latest `failure`; only an older run of the same name is ignored. An older run that never ended no longer keeps the head `agk:ci-running` once a newer run of its name has ended.
3. **A skipped run is never the latest of a name that has a run that was not skipped** (the verdict on 4c69972): every push to a pull request branch also starts the `push` workflows, whose `governance` and `agk-route` jobs are skipped by their `if:` and carry the same names, sometimes with a higher `id` than the real run; a name with only skipped runs keeps its newest, and a skipped run is neither red nor pending.
4. **Commit statuses** keep the latest status of each context (`latest_statuses`, the highest `id`), as GitHub does. The router job `agk-route` is still left out by name.
5. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-si.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. Amendment 79 (`docs/runs/proposed-spec-amendments-79.md`) is for SPEC-0032 rules 2 and 7.

## Consequences

- A green pull request whose only red check run was cancelled or replaced is no longer labelled `agk:ci-red`, and the red-branch brief no longer opens for a replaced run of the default branch.
- A run that is really red on its latest run stays red; the router stays the only writer of labels and runs no agent.

## Residual

- 2026-10-26: the router cannot tell a latest run that was cancelled by a person or by `cancel-in-progress` from one that failed; both stay red, as the brief rules, and the next run of the check replaces it (due 2026-12-31).

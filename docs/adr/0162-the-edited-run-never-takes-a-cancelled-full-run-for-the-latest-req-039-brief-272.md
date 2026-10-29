# ADR-0162: the edited run never takes a cancelled full run for the latest (REQ-039, brief 272)

- Status: Accepted
- Date: 2026-10-27
- Deciders: maintainers
- Related: ADR-0137, ADR-0144, ADR-0159
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #272 (priority 0). On pull request #271, head dd2f203 had two `governance full` runs created in the same second
(2026-10-26T20:52:15Z). The workflow's concurrency group cancelled one (40399457998); the other succeeded (40399458037).
`full_run.py` took the latest full run with `max(..., key=created_at)`, which on a tie returns the run the API lists first,
here the cancelled one. So the `governance edited` run and its re-run failed at `Latest full run` on a green head, and the
pull request was labelled `agk:ci-red`. The cause was reproduced first with a fixture of that pair, the cancelled run listed
first. On the unchanged tree `full_run.py` asked for the cancelled run's jobs (`jobs 40399457998`, exit 4), not
`ok full-run`. The tests were written first; 4 of the new tests of `tests/kit/test_full_run.py` failed on the unchanged tree.

## Decision

1. **The latest full run** (answer 1). A full run whose conclusion is `cancelled` is set aside while another full run of the
   head is not cancelled. Among the rest, the latest is the one with the newest `created_at`, and a tie goes to the larger run
   `id` (`full_run.newest`, `full_run.live`). A run still queued or in progress has no conclusion, so it is never set aside, and
   it is still waited for.
2. **Only cancelled runs** (answer 2). When every full run of the head is cancelled, all of them stay. The newest, by the
   same order, is asked for (exit 4), and its jobs then refuse with rule 2, as before.
3. **Tests** (answer 3). In both list orders, the #271 pair reads the green run and passes. A newer cancelled run never beats
   an older green one. A tie between runs that are not cancelled goes to the larger id. Only cancelled runs behave as before,
   and a running run is still waited for. A newer failed run still beats an older green one.
4. **The router** (answer 4). The router (`route.py latest_runs`, brief #229) reads check runs by the highest `id`, so a
   cancelled run that a newer run replaced never decides a label. With this change, `full_run.py` also never lets a replaced
   cancelled run decide, and it breaks a tie the same way, by the larger id. The two do not read in one and the same way. The
   router still counts a cancelled run that is the newest run of its name. `full_run.py` sets a cancelled full run aside whenever
   a run of the head that is not cancelled exists, whatever their order (Q-272-1).
5. Flow mode: fragment `changelog.d/cancelled-full-run.md`, no version bump. `kit/hashes.json` is a release file and is not
   edited here (session rule 14).

## Consequences

- A push followed at once by a description edit no longer turns a green head red through a cancelled twin of its full run.
- A head whose only full runs were cancelled still needs a push or a re-run, as before.

## Residual

- 2026-10-27: Q-272-1, whether the router should also set a newest cancelled run aside when an older run of the same name
  completed (it counts it today, as GitHub's required check does), is for the maintainers (due 2026-12-31).

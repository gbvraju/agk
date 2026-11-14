# ADR-0513: The router reads local evidence in local mode

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0032, SPEC-0039, ADR-0182, ADR-0385, brief #1212, plan #661
- Requirements: REQ-039

## Context

In local mode (GitHub Actions blocked, `docs/guides/local-mode.md`) the router's job does not run, and the guide says no
`agk:` label moves. Run by hand, `route.py` reads the required checks of every head as never reported and sets
`agk:ci-running` on every pull request, which `session.py review-queue` skips, so the conductor would stall. The guarded
merge already reads local evidence: the verdict's `Local evidence: <sha>` and `Evidence check: agrees, head <sha12>`
(`merge_cleared.local_evidence`), with the open local-mode record issue as the switch.

## Decision

1. `scripts/agk/route.py`: while a local-mode record issue is open (title `Local mode since ...`, found as
   `merge_cleared.local_mode` finds it; the open issues are read once per run, and open issues that cannot be read count as
   none), a required check of the head that never reported is satisfied when the newest `Report:` of the pull request's
   author on that head carries the `Evidence: prepush schema <n>, head <sha12>, <n> steps ok, record <sha12>` line naming
   the head, and failed (`agk:ci-red`) when that report carries a `prepush: stopped at ...` or `failed: step ...` line.
   Without either the head is the builder's (`agk:build`); the router never sets `agk:ci-running` for checks that never
   reported. A check that reported (running, red or green) is judged as before, so a red check still blocks.
2. In that mode `agk:merge-ready` also needs the latest verdict's local evidence for the head, read by
   `merge_cleared.local_evidence` itself (its two patterns and the `Maintainer answer: accept <sha>` exception, no copy);
   without it a cleared head is `agk:review`. `agk:owner-merge` and every other state and their order are unchanged.
3. `route.py --all` and `--pr N` work in local mode with the person's own `gh`; `docs/guides/local-mode.md` replaces "No
   router labels" with one paragraph: the conductor runs `route.py --all` once per review pass, and step 3 (the unfreeze)
   is needed only with an older kit.
4. Without an open record issue nothing changes.

## Consequences

Labels follow the local evidence, so the owner and the business see each pull request's state without GitHub Actions, and
`review-queue` no longer skips every pull request as `checks running`. A builder puts the `Evidence:` line in its
`Report:` as well as in the body. `tests/kit/test_route_local.py` covers matching evidence (`agk:review`), a failed step
(`agk:ci-red`), a cleared verdict with `Evidence check: agrees` (`agk:merge-ready`), `differs` or a stale head (not
`agk:merge-ready`), no record issue (unchanged) and `route.py --pr N` against a `gh` stub; the existing
`tests/kit/test_route*.py` stay green. Protected path classes changed: `scripts/agk/` (`route.py`), `tests/kit/`
(`test_route_local.py`) and `agk.toml` (the new test file in the test map of `route.py` and `merge_cleared.py`, which
`tests/kit/test_always_full_infra.py` requires). No workflow, ruleset or `.claude/agents/` file changes.

## Residual

- 2026-11-14: the router reads the `Evidence:` line from the builder's `Report:`, not from the record file; the conductor's
  `evidence.py check` stays the proof behind `agk:merge-ready`. Whether the builder evidence should also be read from the
  pull request body is left to the maintainers (Q-1212-1, due 2026-12-31).

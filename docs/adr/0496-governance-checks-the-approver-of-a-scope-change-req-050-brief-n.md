# ADR-0496: Governance checks the approver of a scope change

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: SPEC-0043, ADR-0467, ADR-0269, `Q-1095-1`, brief #1166, brief #1095, plan #661
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `.github/`

## Context

ADR-0467 (brief #1095) lets `scripts/agk/check_plan.py` treat a scope change as approved by its `Approved: <date>
<link>` line, and only with `--comments FILE` also require a listed approver's `Approve: scope SC-<n> <full head
ID>`. On the default branch at 71b6ba0 the governance job runs `python scripts/agk/check_plan.py` with no
`--comments` (`.github/workflows/governance.yml` line 257), although an earlier step of the same job saves the pull
request's comments to `$RUNNER_TEMP/comments.json` (line 183). ADR-0467's first residual records the gap, and the
conductor's ruling on `Q-1095-1` (#1147) asked for this follow-up.

## Decision

1. On a `pull_request` event the governance job's `check_plan` step runs `python scripts/agk/check_plan.py
   --comments "$RUNNER_TEMP/comments.json"`; on any other event (a push) it runs `python scripts/agk/check_plan.py`
   as before, since that event saves an empty list and an empty list would withdraw every approval on the default
   branch. The workflow line is the owner's to commit (brief #1166 answer 1).
2. With the saved comments, an approved scope change whose whole block (every line, its `Briefs:` entries and its
   `Approved:` line) the merge base already holds unchanged keeps its approval: it was approved on the pull request
   that merged it, whose comments a later pull request does not carry. A new block, or one that differs from the
   merge base's, needs the approver's line on this pull request. Outside a git work tree, or outside CI with no
   base, no block is carried, the stricter reading; a base that does not resolve in CI fails, as rule 20's
   comparison does (`common.resolve_base`). Without this, every later pull request of a project with one approved
   scope change would fail rule 22 once decision 1 is in.
3. A local run (`agk.mk` line 21) and a push read the `Approved:` line alone, as today: they have no pull request
   comments. Personal mode has no pull request comments and is not changed.
4. A comments file that cannot be read, or is not a list, fails with exit 2 naming `--comments`, never a pass and
   never a fallback to the `Approved:` line alone (principle 11); this was already so and is now tested.

Protected path classes changed: `scripts/agk/` (`check_plan.py`: `merged_approvals` and the base passed to
`approved_ids`), `tests/kit/` (`test_check_plan_scope.py`; `test_workflow.py`, whose step test reads a `run: |` step's `python` lines), `tests/kit_dev/` (`test_init.py`, whose `ci_steps` takes the pull request branch of that step, the event it simulates) and `.github/` (`.github/workflows/governance.yml`, the
`check_plan` step, committed by the owner). `kit/hashes.json` is not edited by hand.

## Consequences

In the pull request checks a scope change counts as approved only when a listed approver's `Approve: scope` comment is
on that pull request, or the approved record merged earlier unchanged; an `Approved:` line typed into the file is no
longer enough there.

## Residual

- 2026-11-13: the head named by `Approve: scope SC-<n> <full head ID>` is read for its shape, not compared with a head
  of the pull request (ADR-0467 decision 4 as built) (due 2027-01-31).
- 2026-11-13: an approved block merged before decision 1 was in was never checked against its approver; it is
  carried as approved by decision 2 (due 2027-01-31).

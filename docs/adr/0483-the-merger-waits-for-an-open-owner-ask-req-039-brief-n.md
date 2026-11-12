# ADR-0483: The merger waits for an open owner ask or spec approval

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: ADR-0265, ADR-0304, ADR-0387, brief #1101, brief #1134, plan #661
- Requirements: REQ-039

## Context

On 2026-11-12 the owner directed that owner asks go on the item itself (brief #1101). `route.py` `base_state` returns
`agk:question` for an open `Owner needed:` before it reaches the `agk:approve` state, so a pull request that needs a
spec approval and carries an owner ask is labelled `agk:question`, never `agk:approve`. `merge_cleared.py` `unapproved`
held only on the label `agk:approve` or an `Approval: SPEC-nnnn` line of the pull request's body; it never read the
`Approval:` line of the clearing verdict, and no hold of SPEC-0039 rule 5 named `agk:question`. #1132 (amendment 168 of
SPEC-0030) carried `Approval: SPEC-0030` in its covered fix list and an `Owner needed:` asking for `Approve: SPEC-0030`;
the merger run 43283562751 merged it at 18:51:23Z with no approval on it.

## Decision

1. SPEC-0039 rule 5 gains two holds (amendment 170, `docs/runs/proposed-spec-amendments-170.md`):
   - (a) a pull request labelled `agk:question`, an open owner ask (`owner ask`);
   - (b) a pull request whose clearing verdict (the latest `Verdict:` by a listed verdict author naming the head)
     carries an `Approval: SPEC-nnnn` line for a spec with no approval for that head, read exactly as the body's line
     is read today (`spec approval`), including amendment 124's approval of an earlier commit whose spec text the head
     keeps.
2. Both are built in `merge_cleared.py`: `asked_specs` reads the verdict's `Approval:` lines beside the body's,
   `unapproved` and `spec_waiting` use it, and the hold list holds on `agk:question` right after `hold label`. So
   `--status` reports them as pending the same way (`owner ask (rule 5)`, `approve SPEC-nnnn`), and the merge queue,
   which judges each pull request with the same hold list, waits too.
3. No change to `route.py`, the labels, `conductor.py` or any workflow. The owner approves with
   `Approve: <head> SPEC-nnnn` on the pull request; no session posts it.

Protected path classes changed: `scripts/agk/` (`merge_cleared.py`), `tests/kit/` (`test_merge_cleared_owner_ask.py`),
`tests/kit_dev/` (`test_conductor_catches.py`: the row count of the catch log) and `agk.toml` (the new test file in
the `[[testing.map]]` entry of `scripts/agk/merge_cleared.py`).

## Consequences

A cleared head with an open owner ask, or whose verdict names a spec approval that is not in, stays unmerged until the
owner answers: the label leaves when the ask is answered, and the `Approve:` line releases the spec approval. A verdict
that only mentions `Approval: SPEC-nnnn` in its prose also holds (fail closed); the conductor writes the line only when
it means it. A pull request the router labels `agk:question` for any open owner ask (a size ruling, as on #1130) waits
for it as well.

## Residual

- 2026-11-12: `conductor.py`'s status line for a cleared head names the missing spec from the body's `Approval:` lines
  only, so a verdict-only approval shows as `waiting: Approve label`; the merge reads it correctly (due 2027-01-31).

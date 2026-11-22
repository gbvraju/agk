# ADR-0718: A covered fix list with only ADR Final lines carries to the light re-prove's merge (REQ-057)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0277, ADR-0495, SPEC-0021, SPEC-0039, SPEC-0050, brief #1714, brief #1163, brief #1616, plan #661
- Requirements: REQ-057

Protected classes this pull request changes: `scripts/agk/` (`merge_cleared.py`) and `tests/kit/`
(`test_light_reprove.py`). `kit/hashes.json` is not edited by hand. The amendment of SPEC-0050 rule 7a is proposed in
`docs/runs/proposed-spec-amendments-216.md` and is applied only on the spec approvers' approval (principle 6).

## Context

SPEC-0050 rule 7a (amendment 171, ADR-0495) carries a clearing verdict on the old head to the light re-prove's merge
of the default branch, when that merge adds nothing beyond the default branch's change. It says "a fix list with
`Final:` lines never carries". SPEC-0021 rule 3a (ADR-0277) made a covered fix list whose `Final:` lines all read
`docs/adr/<file> Proposed -> Accepted` the clearing verdict of the head it names, so nearly every head that adds an ADR
is cleared that way (12 of the 13 pull requests merged on 2026-11-22). None of them can carry: each merge that touches
a shared index sends the others back for a full review round (brief #1714, the conductor's report on #661).

## Decision

1. `merge_cleared.carried_from` returns the old head a carried verdict names: the latest verdict, by an allowed
   author, is `Verdict: cleared <old>` or a covered fix list on `<old>` that `accepted_adrs(verdict, <old>)` reads as
   ADR accepts only; `<old>` is not the head; and `session_plan.light_merge(root, <old>, head, default, shared)`
   holds. Otherwise None. `judge_carried` clears on it; `judge` is unchanged.
2. `merge_cleared.judge_named` returns the state, the reason and the head the clearing verdict names (the head itself,
   or `<old>` after a carry). `holds` and `verdict_state` pass that head to `accepted_adrs`, and
   `acceptance_lines(repo, sha, verdict, named)` reads each ADR's status at the new head SHA, which must be
   `Proposed`, and writes `ADR-nnnn Accepted (Final <comment id>)` as before. `hold_list`'s check that each accepted
   ADR is one the pull request adds or changes is unchanged.
3. `[flow] shared_indexes` of the default branch is read as `session_plan.shared_indexes` reads it: a value that is
   not a list of exact paths (no wildcard, no folder) is no carry, the plain `judge` reason, never a pass.
4. Unchanged: the required checks of the new head, every hold of SPEC-0039 rule 5, the pre-merge governance run,
   `answered` (exact to the head, Q-1616-1) and `local_evidence` (rule 4, exact to the head). A fix list with a
   numbered item, a `Final:` line on `docs/requirements.md` or a stack-options ADR never carries.
5. One step only (Q-1714-2): two light merges in a row do not carry, since `light_merge` needs `<old>` as the first
   parent. In local mode the old head's evidence does not carry (Q-1714-3).

## Consequences

A shared-index catch-up merge of a head cleared with its own ADR accepts no longer needs a new review, and its ADRs are
still accepted in the squash. In local mode the carry clears rule 3, and rule 4 still holds until a verdict names the
new head's local evidence. Every `agk.toml` setting reads as before: `[flow] auto_merge` off is refused before any
judge, `max_behind_merges`, `merge_queue`, `conductor_lapse_minutes`, `execution`, `review_mode`, `pr_mode` and
`[governance] level` are read beside the carry, unchanged; personal mode has no merger.

## Residual

The amendment of SPEC-0050 rule 7a waits for the spec approvers (2026-11-22).

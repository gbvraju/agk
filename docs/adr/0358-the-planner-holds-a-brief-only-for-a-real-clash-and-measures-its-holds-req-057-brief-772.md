# ADR-0358: The planner holds a brief only for a real clash, and measures every hold

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: amendment 141, brief #772, SPEC-0050, SPEC-0030, SPEC-0006, SPEC-0007, ADR-0189, ADR-0325, ADR-0339, ADR-0357
- Requirements: REQ-057

## Context

On 2026-11-08 `session.py plan` started 0 of 9 builders while 4 pull requests were open. Of 11 waiting briefs, 6 waited on one
blocked pull request, 5 of those only because their `Touches:` named a whole folder, and 3 more waited on shared prose that
git merges by line. Two pieces of work reserved one amendment number. The rules of SPEC-0050 are sound for files named
exactly; the waste comes from what they are given and from what nobody ranks (brief #772, the owner's request quoted there).
Measured again on 2026-11-09: 6 of 21 open briefs have a broad entry over files that can hold a brief.

This pull request adds only this file and `docs/runs/proposed-spec-amendments-141.md`, and changes no protected path. The
builds it covers change the protected path classes `scripts/agk/`, `tests/kit/`, `.claude/` (the conductor's work list and,
if `Q-772-10` is ruled so, its guard), `config/` (the session rules and the rule budget) and, by the same ruling,
`docs/requirements.md`. They need no ADR of their own while they stay within this one (session rule 36).

## Decision

1. `Touches:` names the existing files a brief edits, and a new line `Adds:` names what it creates. A folder or wildcard entry
   matching more than `[flow] max_touch_glob` files that can hold a brief is refused, unless the brief says `Broad: <reason>`.
2. The files fall into four classes in one table: shared-mechanical, shared index, prose (the new `[flow] reprove_paths`) and
   everything else. Only the last holds a brief. All four re-prove under SPEC-0050 rule 6, which does not change.
3. `session.py plan` ranks the open pull requests by the briefs they hold; the conductor works in that order and reports a
   holder idle over `[flow] stall_minutes`.
4. A reservation another open brief or pull request holds is refused, and the later brief gets the next free number.
5. `session.py plan --what-if DIR` shows how a wave would split before it is filed.
6. Each hold is recorded and marked false when the two merged diffs change no common line; the weekly report gives the rate
   and the worst entry or class. The home of the record is the owner's (`Q-772-1`).
7. Every mode reads the same `[flow]` keys and defaults. No workflow, ruleset, required check or network call in a check is
   added.

The full text, with its twelve questions and their readings, is amendment 141. The amendment needs a person's `Approve:` for
each spec it names before any build starts.

## Consequences

More work runs at once, and the later of two changes to shared prose pays one merge of the default branch and one more run
of the required checks. Every open brief with a broad entry is refused once build (a) merges, so the repair goes with it.
`Touches:` must be written with care, and a brief that truly sweeps a folder says so.

## Residual

- 2026-11-09: two changes to one prose file can merge cleanly and still disagree in meaning; the conductor's review of the
  diff since its last verdict (SPEC-0050 rule 6) is the only guard (due 2027-01-31).
- 2026-11-09: a brief held by a taken brief with no pull request yet is not ranked by decision 3, which ranks pull requests
  as the brief asks; the waiting line still names it (due 2027-01-31).
- 2026-11-09: until `Q-772-1` is ruled, the false-hold rate on this repository reads `unknown` and the defaults of decisions
  1 and 2 are not tuned by evidence (due 2026-12-31).
- 2026-11-09: `docs/runs/holds.jsonl` only grows; a retention rule waits for a measure of its size (due 2027-03-31).

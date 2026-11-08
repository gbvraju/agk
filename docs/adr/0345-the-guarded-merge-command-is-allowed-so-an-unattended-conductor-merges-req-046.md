# ADR-0345: The guarded merge command is allowed so an unattended conductor merges (REQ-046)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0265, SPEC-0039, amendment 136, ADR-0341, plan #661
- Requirements: REQ-046

Protected classes: `.claude/`, `docs/specs/`, `tests/kit/`

## Context

SPEC-0039 rule 8 lets only the conductor merge, through `merge_cleared.py`, and `Q-S0039-15` read that builders are held
back by an `ask` entry in `.claude/settings.json` while the conductor's guard hook allows the command. A scheduled
conductor session cannot answer an `ask`, and the guard hook's `allow` did not lift it there: on 2026-11-08 the scheduled
merge runs for #715 and #734 were refused, cleared pull requests waited, and an attended session merged them by hand.

## Decision

1. `.claude/settings.json` moves exactly `Bash(python3 scripts/agk/merge_cleared.py*)` from `ask` to `allow`.
2. `Bash(python scripts/agk/merge_cleared.py*)` and `Bash(*conductor.py*merge-queue*)` stay on `ask`; the wildcard form
   `Bash(*merge_cleared.py*)` is removed, because an `ask` that matches beats an `allow`. Nothing is denied.
3. Builders stay blocked from any merge by session rule 2 and their launch prompt; the gate is the script's re-checks
   (a cleared verdict on the exact head from another session, green required checks, the owner's approvals).
4. SPEC-0039 rule 8 and `Q-S0039-15` say so (amendment 136); the two settings tests pin the new lists.

## Consequences

- Scheduled conductor sessions merge cleared pull requests within minutes, as `[flow] auto_merge = true` intends.
- A builder that broke session rule 2 could run the command; it would still merge only a head that another session
  cleared with green checks and the owner's approvals, so nothing uncleared reaches the default branch.

## Residual

- The guard hook's `allow` not lifting a settings `ask` in scheduled sessions is observed, not documented; if a later
  runtime honours it, the entry can move back to `ask` by another amendment.

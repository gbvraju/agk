# Proposed spec amendments 60 (SPEC-0034; REQ-039)

Date: 2026-10-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0123. The path: `docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md`.

1. **SPEC-0034 rule 2, the brief the router writes.** The shape of a brief (`Advances:` REQ-n or `new`, `Touches:`, `Priority:` 1 to 3) has one exception, written only by the router (SPEC-0032 rule 7): the pair `Advances: none` and `Priority: 0` together, which marks the brief of a red default branch. Either line alone is a problem, and no other brief may use `Priority: 0`. The router also writes `Touches: **`, which `session.py next` reads as every path. `brief_problems` accepts the pair and nothing else changes for an ordinary brief.

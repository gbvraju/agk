# ADR-0729: A take adds reserved numbers only when the owner posted it (REQ-037)

- Status: Accepted
- Date: 2026-11-22
- Deciders: maintainers
- Related: SPEC-0058, brief #1711, brief #1729, brief #1731, Q-1711-1, Q-1731-1
- Requirements: REQ-037

Protected classes this pull request changes: `scripts/agk/` (`session.py`) and `tests/kit/` (`test_injection_set.py`,
`test_session_prompt.py`). `kit/hashes.json` is not edited by hand.

## Context

`session.reserved_numbers` builds the `Reserved:` line of the builder prompt (`session.py prompt`, SPEC-0058 rule 7:
no GitHub text goes in). It added the `reserves` of every take comment on the brief, whoever posted it, so a comment
`taken: x9 <date> reserves ADR-0999` by any account put `ADR-0999` into the prompt (found-bug #1731, found by the
injection set of brief #1711). The text is a number form only, never free text, but a builder could write an ADR, spec
or requirement under a number nobody reserved. The owner ruled Q-1711-1 on 2026-11-22 at 15:10Z: in solo mode a take
counts only when its comment is the owner's; the team-mode rule follows the required role approval and is parked.

## Decision

1. `reserved_numbers` adds a take's `reserves` only when the take comment's `author_association` is in
   `TAKE_ASSOCIATIONS`, which is `("OWNER",)`, the value of `merge_cleared.INSIDE_ASSOCIATIONS` (brief #1729). A
   comment without that field counts as not the owner's. The brief's own `Reserved:` lines are read as before.
2. With `review_mode = "team"` the same rule holds until Q-1731-1 is ruled: only an owner's take adds numbers, the
   conservative reading. The team-mode rule (the required role approval) is not built here.
3. Who holds a take (`all_takes`, `live_takes`, `claim`, `released:`) is unchanged.

## Consequences

A stranger's take comment no longer reaches a builder prompt. A take posted by a collaborator's or a member's account
adds no number either; in solo mode every session posts under the owner's account, so a real take still counts. The
`xfail` mark for #1731 in `tests/kit/test_injection_set.py` is removed and the case passes.

## Residual

- 2026-11-22: Q-1731-1, the team-mode rule (which role's take counts, and how a comment's author is matched to that
  role), is open for the maintainers.

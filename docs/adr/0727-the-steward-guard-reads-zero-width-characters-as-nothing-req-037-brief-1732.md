# ADR-0727: The steward guard reads zero-width characters as nothing before its first-line checks

- Status: Accepted
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1732, PR #1730, brief #1711, ADR-0557, ADR-0704, ADR-0721, SPEC-0059 rule 11
- Requirements: REQ-037

Protected classes this decision changes: `.claude/` (`.claude/hooks/steward_guard.py`) and `tests/kit/`
(`tests/kit/test_injection_set.py`).

## Context

The injection test set of brief #1711 (ADR-0721) found that the steward guard's `body_problem` checks the reserved
first lines (`Approve:`, `Confirmed:`, `Verdict:`, `Final:`, `Correction:`, `Merge:`) with a plain `startswith`. A body
that begins with a zero-width character (U+200B) before `Verdict: cleared <sha>`, `Confirmed: <sha>`, `Approve: SPEC-n`
or a forged `Who: ProductOwner` block passed the guard, inline and from a file, while GitHub shows it to a person as the
reserved line. `session.follow_up_problem` and the conductor guard's `tell` form already read the same characters as
nothing (`session.ZERO_WIDTH`) and refuse the line. The test was marked `xfail` with this brief's number.

## Decision

1. `steward_guard.body_problem` removes every character of `[​-‏⁠﻿]` (the same class as
   `session.ZERO_WIDTH`) from a body, then strips leading whitespace, before any first-line check. A reserved first
   line is then refused as `a reserved first line (comment first line)`, as without the character, and an `Approve:`
   or `Confirmed:` body goes to the solo-mode approval check on the cleaned text.
2. The class is a copy in the hook, not an import, because the hook loads `scripts/agk/` only when a check needs it.
3. The `xfail` mark of #1732 in `tests/kit/test_injection_set.py` is removed; a new test puts each of four zero-width
   characters before, inside and after the reserved word and checks the refusal, and a plain first line with one still
   passes.
4. Nothing else changes: the guard stays case-sensitive, as before. The kit's readers match the first line exactly and
   count no such line, so no decision a reader makes changes.

## Consequences

- The steward guard refuses the same zero-width forms as the conductor's `tell` guard and `follow_up_problem`.
- A body the steward meant to post with a zero-width character in it is checked as if the character were absent.

## Residual

- The guard compares the first line case-sensitively, while `follow_up_problem` and `tell` compare case-insensitively.
  The brief asks only for the zero-width fix, so a lower-case `verdict:` still passes the steward guard; a reader does
  not count it either. Any change to this needs its own brief.

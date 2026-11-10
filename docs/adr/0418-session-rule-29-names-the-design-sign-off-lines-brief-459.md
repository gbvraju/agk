# ADR-0418: Session rule 29 names the design and inventory sign-off lines

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: SPEC-0037 rule 9, brief #976, brief #459 answer 6, Q-459-1 on #949, ADR-0310
- Requirements: REQ-044

Protected classes: `config/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0037 rule 9 says that only an account of `spec_approvers` gives the `Approve: inventory` and `Approve: design`
lines, that a session never posts them and prints them in solo mode, and that a session then appends a row to
`docs/design/signoffs.md`. A session reads `config/session-rules.md`, not the spec, so it did not meet that rule
where it works. The owner ruled on #949 (Q-459-1) that answer 6 of brief #459 is built in its own brief, because
the rules file may not grow past its line in `config/rule-budget.txt`.

## Decision

1. Session rule 29 gains one sentence, inside the rule: the two lines go on the inventory's or the prototype's pull
   request, only an account of `spec_approvers` gives them, a session never posts them and in solo mode prints them
   inside the `Confirmed:` text, and after one it appends one row from `date -u` in a commit that changes only
   `docs/design/signoffs.md` (SPEC-0037 rule 9). No rule line is added and no rule is renumbered.
2. To pay for it, explanations and examples that require nothing are cut: the two parentheses on why `watch` is not
   run in the foreground or detached (rule 10), the parenthesis of example foreseeable stops (rule 7, which still
   says "before any stop it can foresee"), the list of example blocks (rule 21, which still says "for any reason"),
   the sentence on why a brief stays open (rule 28) and the list of example `tell` messages (rule 32). Rule 11 keeps
   "the conductor keeps no state of its own", which SPEC-0032 rule 3 requires. Every requirement stays;
   `tests/kit_dev/test_session_rules_push.py` pins rule 7's milestone without the cut parenthesis.
3. The file's line in `config/rule-budget.txt` drops from 3448 to 3431 words.
4. `tests/kit/test_session_rules_signoff.py` reads rule 29 and finds the sentence.

## Consequences

A session reads the sign-off rule in its own rules. The rules file is seventeen words shorter. The spec is unchanged.

## Residual

None.

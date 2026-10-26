# ADR-0163: a stack ADR is accepted in one plain step (REQ-036, brief 274)

- Status: Proposed
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0080, ADR-0159
- Requirements: REQ-036

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `skills/`

## Context

Brief #274 (priority 1). In a project pilot (2026-10-26) the session proposed to accept the stack ADR written by `/agk:stack` by a
`Final:` commit that sets both `Status: Accepted` and `Chosen: Option A`. A `Final:` commit may change only status lines (SPEC-0021
rule 3), and `engines.py stack-check` refuses a `Chosen` other than `none yet` while the ADR is Proposed (SPEC-0029 rule 5), so the
`Final:` route can never accept a stack ADR; only an ordinary commit that changes both lines works, and no text said so. The cause
was reproduced first: on the unchanged tree a `Final:` commit that set both lines failed with the generic `rule 3: the commit is not
exactly the named status lines`, and an Accepted lock with a one-line reason (`Option A — <reason>`) failed `stack-check`, since only
a bare `Option <X>` was read. The tests were written first and were red on the unchanged tree (4 of
`tests/kit_dev/test_engines_stack.py`, 1 of `tests/kit/test_final_clearance.py`).

## Decision

1. **The documented way** (answer 1): one ordinary commit, in its own pull request, sets `Chosen: Option <X>` with a one-line
   reason and `Status: Accepted` together. `engines.py stack-check` accepts an Accepted lock that is one line, `Option <X>` or
   `Option <X> — <reason>` (the same dash as the options), naming one of the ADR's options; anything else (no reason after the
   dash, two options, an option the ADR does not hold, a second line) fails naming rule 5 and the accepted shapes, never a value.
   The verdict on that pull request is a plain `cleared`.
2. **Chosen while Proposed is still refused**; the message now adds that an option is chosen by one ordinary commit that sets
   `Chosen` and `Status: Accepted` in the same commit.
3. **The skill** (answer 2): the last step of `/agk:stack` says how an option is accepted and prints the prompt for the accepting
   change and the body of its pull request, as text with placeholders. Building and checking that body with `check_pr_body.py`
   is brief #273's (the bodies brief), which touches the same files; this build adds no next-steps command (Q-274-1).
4. **The final-commit check** (answer 3): when a covered final commit is not exactly the named status lines and it changes the
   `Chosen` line of a stack ADR (`docs/adr/<n>-stack-options.md`), `check_final_clearance.py` fails with `rule 3: a stack's Chosen
   line is set by an ordinary commit, not a Final commit`; any other extra change keeps the existing rule 3 message.
5. The reference guide says the same in the `/agk:stack` paragraph. Flow mode: fragment `changelog.d/stack-accept.md`; no version
   bump, and `kit/hashes.json` is not edited (session rule 14).

## Consequences

- A person accepts the stack in one pull request with one commit, and the checks pass it without a fix list or a `Final:` line.
- A session that tries the `Final:` route is told why it fails and what to do instead.
- An Accepted stack ADR whose lock carries a reason in another shape (a colon, a full stop, a second line) fails `stack-check` and
  is rewritten to `Option <X> — <reason>`.

## Residual

- 2026-10-26: Q-274-1, whether `/agk:stack` should print the accepting body from a script checked by `check_pr_body.py`, is left
  to brief #273 (due 2026-12-15).
- 2026-10-26: Q-274-2, the reason's shape is read as the dash of the options only; whether another separator should pass is for the
  maintainers (due 2026-12-15).

# ADR-0228: the stack ADR names the testing practices and the [testing] settings a new project starts with (REQ-016, brief 418)

- Status: Proposed
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0176, ADR-0180, ADR-0220
- Requirements: REQ-016

Protected classes: `kit/`, `skills/`, `tests/kit_dev/`

## Context

The stack ADR template already carries the local-profile (brief #267) and fast-CI (brief #283) practices; testing has none.
In the pilot the suite took 8 to 10 minutes for 811 tests. The `[testing]` table of `agk.toml` (brief #373, ADR-0220) says
which tests guard which code, but nothing sets it when a project chooses its stack. Brief #418 gives the answers.

## Decision

1. **Two practices in the template (answer 1).** The Practices list of `kit/templates/stack-adr.md` gains
   `fast tests: check (step: the full project suite runs in budget_seconds or less on the CI runner, with tests in parallel, a
   template database copied per test, no network in tests and cached dependencies)` and `test selection: judgement (the
   [testing] profile and the always_full paths the option proposes, for example authentication, permissions, migrations and
   secrets handling)`, verbatim from the brief. Both pass `stack-check` as written.
2. **One ADR sets the values (answer 2, Q-418-1).** `skills/stack/SKILL.md` says that the build which accepts the stack copies
   the chosen option's `[testing]` values into `agk.toml` in the same pull request as the ADR. Read conservatively, within the
   brief's `Touches:` line and with no script change: "the build which accepts the stack" is the accepting pull request the
   skill already describes; the values are copied by a second ordinary commit in it, after the unchanged two-line accepting
   commit, and the printed prompt names that commit. For the values to be in the ADR before they are copied, the skill's
   drafting step has the architect write, in the parenthesis of `test selection`, each option's `[testing]` profile and
   `always_full` paths of `agk.toml`; the ADR then names `agk.toml`, so the protected-changes check counts the accepting
   pull request's change of that file as covered by the stack ADR.
3. **Tests first (answer 3).** `tests/kit_dev/test_stack_adr_testing.py` checks both lines of the template, that the earlier
   practices stay, that `stack-write` renders both lines, that a stack drafted from the template with them passes
   `stack-check`, and that the skill names the copy, its pull request and the prompt's second commit.

## Consequences

A new project is fast and selected by construction from its first build: the adopting build adds the `fast tests` step as a
governance check, and the accepting pull request sets `[testing]` from the same ADR. `stack-next-steps` is unchanged: the body
it prints for the accepting pull request does not mention the `agk.toml` commit.

## Residual

- 2026-10-31: Q-418-1 (decision 2): whether `stack-next-steps` or `stack-check` should check that the accepting pull request's
  `[testing]` table matches the chosen option is a later brief.

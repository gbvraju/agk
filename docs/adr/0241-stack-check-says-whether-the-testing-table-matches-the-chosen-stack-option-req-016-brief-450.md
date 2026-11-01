# ADR-0241: stack-check says whether the [testing] table matches the chosen stack option (REQ-016, brief 450)

- Status: Proposed
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0220, ADR-0228
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

ADR-0228 (brief #418) has the pull request that accepts the stack copy the chosen option's `[testing]` values into `agk.toml`
by a second ordinary commit, and left as a residual (Q-418-1) whether anything checks that copy. Nothing does: a project can
accept a stack and keep the template's `[testing]` defaults without anyone noticing. Brief #450 gives the answers.

## Decision

1. **One step after `ok engines-stack` (answer 1).** `cmd_stack_check` in `scripts/agk/engines.py`, once the shape check passes
   and only when the one stack ADR is Accepted with a `Chosen` line that names an option (`accepted_stack`, `CHOSEN_LINE`),
   reads the `test selection` bullet of the Practices item and takes from it the chosen option's part: the text after
   `Option <X>` up to the next `Option <letter>`, or the whole parenthesis when it names no option (Q-450-2). From that part it
   takes the profile, one of `impact.PROFILES` named as a word, and the `always_full` paths named in backticks (a backticked
   profile name, a `[testing]` setting name or `[testing]` itself is not a path). It compares them with `[testing]` in
   `agk.toml`, read through `impact.testing_table`, so a missing `profile` key compares as its default.
2. **One line, never a failure (answer 2).** It prints `info engines: [testing] matches option <X>` when the profile and every
   named path agree; `info engines: [testing] differs from option <X>: <what>` otherwise, where `<what>` is `profile`,
   `always_full` or both, never a value; and `info engines: [testing] not compared: <reason>` when the ADR has no `test
   selection` practice, the chosen option's part names no profile or more than one (Q-450-3), the table is absent, or
   `impact.testing_table` refuses it (its message, which names the setting). The line comes before the local-profile line. The
   exit code stays what the shape check gives. A Proposed ADR, whose `Chosen` is `none yet`, gets no line at all (Q-450-1).
3. **Conservative readings (answer 3).** A part that names no profile is never read as a mismatch, and a path listed in
   `agk.toml` but not in the bullet is not a difference: the bullet's paths must be a subset of `always_full`.
4. **Text (answer 4).** `skills/stack/SKILL.md` step 4 says that after the second commit `stack-check` prints whether the copy
   matches. `docs/guides/testing.md` names no stack ADR today, so the same sentence is added to its settings section with the
   stack ADR named there (Q-450-4).
5. **Tests first (answer 5).** `tests/kit/test_stack_testing_match.py`, with invented ADRs and `agk.toml` files under a temporary
   root: match; profile differs; a path missing; both differ; an extra path; only the chosen option's part is read; no profile
   in the bullet; the template's own wording; no practice; no `[testing]` table; a refused table; no chosen option yet; and the
   exit code unchanged in every case, with a shape failure still failing. The kit-dev tests that asserted the exact output of
   `stack-check` for an Accepted stack ADR (`tests/kit_dev/test_engines_local_profile.py`, `test_engines_stack.py`) now expect
   the one added line before the local-profile line; nothing else in them changes.

## Consequences

A project that accepts a stack and forgets, or mistypes, the `[testing]` copy sees one line saying so each time `stack-check`
runs. Nothing is copied automatically and nothing fails, as the brief's out-of-scope line says.

## Residual

- 2026-11-01: Q-450-1 to Q-450-4 (decisions 1, 2 and 4) are conservative readings recorded in the pull request.

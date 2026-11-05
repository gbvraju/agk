# ADR-0276: A test never pins its own ADR to Proposed (REQ-009, brief 483)

- Status: Accepted
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0250
- Requirements: REQ-009

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The test of brief #386 asserted `- Status: Proposed` in ADR-0245, the ADR that the same pull request added. The
status-only `Final:` commit of #463 made ADR-0245 Accepted, the test failed and the default branch was red (#472) until
#475 changed the test to accept Proposed or Accepted (ADR-0250, whose residual line says that a test never pins its own
ADR's status). Nothing caught the pattern before the merge. Brief #483 asks for a governance check and one line of
builder guidance. The conductor's field note on #483 reserves this number and gives the answers.

## Decision

1. **The check (answer 1).** `scripts/agk/check_kit_tests.py`, which already owns the hygiene of the kit's tests, gains
   a second rule. When a base ref resolves, it reads every `test_*.py` file that the pull request adds or changes (the
   diff from the merge base to the working tree, as the other diff checks read it) and every ADR under `docs/adr/` that
   the pull request adds. A test file fails when it names an added ADR outside a docstring (`ADR-NNNN`, `adr/NNNN` or
   the ADR's file name in a string) and holds an assertion or a comparison with a string naming `Proposed` and no string
   naming `Accepted`. The message names the test file and the ADR. An ADR already on the base is not affected, and a
   test file the pull request does not touch is not read. Without a base ref outside CI the rule is skipped, as in the
   other diff checks; the installed-test rule runs as before.
2. **The guidance (answer 2).** The rules block of `docs/briefs/TEMPLATE.md` gains one line: a test never pins its own
   ADR's status. `config/session-rules.md` gains no rule.
3. **Tests first (answer 3).** `tests/kit/test_kit_tests_own_adr_status.py` builds fixture repositories; no network.

## Consequences

A pull request whose test pins its own new ADR to Proposed is red on its own head, before the status-only commit can
turn the default branch red. A test that accepts Proposed or Accepted, the form of ADR-0250, passes. The rule runs only
where `kit/manifest.json` exists, the kit repository, like the rest of the check.

## Residual

- 2026-11-04: the rule reads the text of a test, not what it runs, so a test that builds the word `Proposed` at run
  time is not seen; the check narrows the pattern of #472, it does not prove its absence.

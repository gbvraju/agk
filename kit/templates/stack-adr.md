# ADR-{{adr}}: stack options

- Status: Proposed
- Date: {{date}}
- Deciders: maintainers
- Related: none
- Requirements: TODO(architect)

## Context

TODO(architect): what the product needs from a stack, as the owner gave it in the vision and the charter.

## Decision

1. **Options**
   - Option A — TODO(architect). Trade-offs: TODO(architect). External services: TODO(architect). Practices: TODO(architect).
   - Option B — TODO(architect). Trade-offs: TODO(architect). External services: TODO(architect). Practices: TODO(architect).
2. **Practices**
   - TODO(architect): check (step: the governance step the adopting build adds) or judgement
   - local profile: check (step: a smoke test that starts the local profile and signs in with the stand-in identity)
   - fast CI: check (step: `agk doctor` reports ci-drafts and ci-concurrency ok for each workflow of required_checks; the five defaults of the kit's guide project-ci.md)
   - fast tests: check (step: the full project suite runs in budget_seconds or less on the CI runner, with tests in parallel, a template database copied per test, no network in tests and cached dependencies)
   - test selection: judgement (the [testing] profile and the always_full paths the option proposes, for example authentication, permissions, migrations and secrets handling)
3. **Chosen**: none yet

## Consequences

The architect accepts one option; the ADR then locks it. Each practice marked `check` is added as a governance step by the build that adopts the stack; each marked `judgement` is recorded here and enforced by review only.

## Residual

None.

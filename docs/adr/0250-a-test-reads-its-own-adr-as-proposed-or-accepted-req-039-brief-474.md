# ADR-0250: A test reads its own ADR as Proposed or Accepted (REQ-039, brief 474)

- Status: Proposed
- Date: 2026-11-02
- Deciders: maintainers
- Related: ADR-0245
- Requirements: REQ-039

Protected classes: `tests/kit/`

## Context

The test of brief #386, `tests/kit/test_core_release_specs.py::test_the_amendment_names_both_paths_and_the_adr`,
asserted `- Status: Proposed` in ADR-0245, the ADR that the same pull request added. Pull request #463 merged at b907a98
with its status-only commit, which made ADR-0245 Accepted. The test then failed, and the governance check on the default
branch failed at b907a98 and on every pull request merged with the default branch after it. Brief #474 fixes the test;
`tests/kit/` is a protected class, so the change needs an ADR that names it. This ADR number was reserved for brief #474
by the conductor (the verdict on #475).

## Decision

The test accepts ADR-0245 as Proposed or Accepted: the ADR holds exactly one `- Status: ` line, and that line reads
`- Status: Proposed` or `- Status: Accepted`. Nothing else in the test file changes.

## Consequences

The status-only commit that accepts an ADR no longer turns the default branch red through a test that reads that ADR.
A test still fails when the ADR has no status line, more than one, or a status other than Proposed or Accepted.

## Residual

- 2026-11-02: a test never pins its own ADR's status.

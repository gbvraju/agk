# ADR-0259: The playbook format and its check (REQ-045, brief 513)

- Status: Proposed
- Date: 2026-11-03
- Deciders: maintainers
- Related: ADR-0251, SPEC-0038
- Requirements: REQ-045

Protected classes: `tests/kit/`

## Context

SPEC-0038 rule 12 build (a) turns a delivery playbook into checked data: a playbook under
`config/playbooks/` is read and checked in governance with no network, so a missing or unknown
section, an unknown work type, an unsupported speed claim or any attempt to lower a gate fails,
naming the rule and the file and never a value (rules 1 to 4, REQ-045 AC1 and AC4). Brief #513
gives the build; ADR-0251 sets the direction and lists the classes the builds of SPEC-0038 change.
This ADR number was reserved for brief #513 by the conductor (the field note on #513).

## Decision

1. The tests of the check come first, in `tests/kit/test_check_playbooks.py`, with fixture
   playbooks under `tmp_path` and invented data only, as SPEC-0038's Tests section lists them for
   rules 1 to 4.
2. Where the reader lives and how the governance step reaches the workflow wait on Q-513-1 and
   Q-513-2 (the pull request body); this ADR is completed with the classes the build then changes.

## Consequences

Until the questions are ruled, only the tests exist and they are red; no check, flow or setting
changes.

## Residual

- 2026-11-03: Q-513-1 (the existing kit-only `scripts/agk/playbook.py`) and Q-513-2 (the workflow
  step that `tests/kit/test_workflow.py` requires beside the `agk.mk` line) are open.

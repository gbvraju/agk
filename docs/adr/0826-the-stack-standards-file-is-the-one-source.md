# ADR-0826: The stack standards file is the one source

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: brief #1975, brief #1974, SPEC-0072 rules 2 and 6, ADR-0817, ADR-0669, ADR-0739, ADR-0313, ADR-0682, ADR-0337, ADR-0259
- Requirements: REQ-079

## Context

ADR-0817 put the Python and Node `[[standards]]` entries in `config/standards.toml` and composes the chosen runtime's
entries for every work type. The web-app, api-service and mobile playbooks still carry their own copies (brief #1638
for Python, brief #1764 for Node), so one stack's pins live in three places and drift when only one is raised.

## Decision

This completes ADR-0817's residual line and amends ADR-0669 and ADR-0739 on where the entries live.

1. The `python-pyproject`, `python-pip` and `node` entries and their comments leave `config/playbooks/web-app.toml`,
   `config/playbooks/api-service.toml` and `config/playbooks/mobile.toml`. `config/standards.toml` is the one source;
   no shipped playbook holds a `[[standards]]` entry. Nothing else in those playbooks changes.
2. A web-app, api-service or mobile project whose Accepted record chose Python or Node runs the same entries it ran
   before (steps, `config`, `rules` tool, version and codes), now from the stack file. The other runtime's playbook
   entries, which were composed but never ran because their pack was off, are no longer composed.
3. A project's own copy of a playbook that still carries the old entries composes them over the stack file's as an
   equal entry, with no refusal and no new doctor line (Q-19Ib-2).
4. The standard screen lists a pack, and says `checked for style and type mistakes`, only once a stack with a pack is
   chosen (Q-19Ib-1).

No setting and no value is added. Baseline files keep their names, because the stack and step names do not change.

Protected path classes changed: `config/` (the three playbooks) and `tests/kit/` (`test_standards_stack.py`,
`test_python_pack.py`, `test_node_pack.py`, and the fixtures of `test_adopt_first_run.py`, `test_skeleton_basics.py`,
`test_playbook_standard.py` and `test_standard_confirm.py`, which now copy or read the stack file).

## Consequences

A raised ruff version or eslint code list reaches every work type at once. A new work type gets a stack's checks
with no playbook edit. Before a stack is chosen, the three playbooks' screens no longer claim language checks.

## Residual

- None: a doctor line for an installed copy that still carries the old entries waits for drift the steward sees
  (Q-19Ib-2).

# ADR-0746: The upgrade skill's test reads the resolver's governance command (REQ-078)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers
- Related: brief #1783, issue #1782, brief #1759, ADR-0737
- Requirements: REQ-078

Protected classes: `tests/kit/`

## Context

#1773 (brief #1759, ADR-0737) changed `skills/upgrade/SKILL.md` step 4 to name
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/kit_root.py" governance` in place of `make governance`. One test,
`tests/kit/test_upgrade_adr.py::test_the_skill_branches_first_writes_the_adr_gates_and_holds_for_the_owner`, still looked
for `make governance` between the `--write-adr` and `--next-steps` lines, so the default branch went red (#1782).

## Decision

1. In that one test the middle index of the order assertion looks for `kit_root.py" governance`. The order it asserts
   (branch, then `--write-adr`, then the gate, then `--next-steps`) is unchanged, so the check is not weakened
   (principle 11). The skill is not edited.

## Consequences

The default branch's governance run turns green. No project using AGK sees a change.

## Residual

None.

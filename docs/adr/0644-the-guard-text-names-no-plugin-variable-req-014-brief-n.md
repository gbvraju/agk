# ADR-0644: The architect guard's description names no plugin variable (REQ-014)

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: brief #1529, brief #1530 (duplicate), issue #1528, ADR-0630, ADR-0631, ADR-0612
- Requirements: REQ-014

Protected classes: `.claude/`

## Context

The default branch is red since #1516 (brief #1500, ADR-0631) merged at 6f7288da: the docstring it added to
`.claude/hooks/architect_guard.py` names the plugin folder variable, which only `scripts/agk/kit_root.py` may name
(REQ-014 AC3, ADR-0630). Three kit tests fail on it: `test_ac3_only_the_resolver_names_the_plugin_variable`,
`test_ac3_no_law_file_depends_on_the_plugin` and `test_ac1_the_role_file_and_guard_name_no_plugin_variable`.

## Decision

1. The one docstring line of `.claude/hooks/architect_guard.py` that wrote the variable out now says "the plugin
   folder variable" instead. No code, no test and no other line changes.
2. The tests' rule stays as ADR-0630 wrote it (principle 11).

## Consequences

The default branch turns green. Nothing a project runs changes, in any mode: one comment line of an installed guard.

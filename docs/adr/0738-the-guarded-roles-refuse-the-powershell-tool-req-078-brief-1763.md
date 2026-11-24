# ADR-0738: The five guarded roles refuse the PowerShell tool

- Status: Accepted
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1763, SPEC-0071 rule 4, SPEC-0059 rule 11, ADR-0612, plan #661
- Requirements: REQ-078

Protected classes: `.claude/`, `tests/kit/`, `tests/kit_dev/`

## Context

On Windows a session has a PowerShell tool beside Bash. Measured on main at 58972e2 on 2026-11-22: the plugin hook ran a
role's guard only for `Edit`, `Write`, `MultiEdit`, `NotebookEdit` and `Bash` (`plugin_hooks.py` `AGENT_TOOLS`), the
five role files' frontmatter hooks matched the same five tools, and each role guard's `decide` allowed every other
tool. So a PowerShell call by the steward, the conductor, the shadow, the architect or the review agent reached no
guard and was allowed: 5 of 5 (brief #1763). The data guard already reads PowerShell lines for every session.

## Decision

1. **The hook sees it.** `plugin_hooks.py` adds `PowerShell` to `AGENT_TOOLS` and also matches the tool name compared
   without case; the five role files (`steward`, `conductor`, `shadow`, `architect`, `architect-review`) add
   `PowerShell` to their PreToolUse matcher. In both layouts (`[kit] layout` installed or `"plugin"`) a guarded role's
   PowerShell call runs its guard.
2. **The guard refuses it.** `steward_guard.py`, `conductor_guard.py` (both modes) and `architect_guard.py` (both
   modes) deny the tool, compared without case, before any other rule, with one line naming the rule and the tool and
   never the command: `<guard>: <rule> denies the PowerShell tool; use Bash (tool: PowerShell)`. A role's PowerShell
   line is refused, not read like Bash (the brief's conservative reading of Q-B3-1): every role has Bash, and one
   reader per tool keeps each guard's rules in one place.
3. **Nothing else changes.** The data guard keeps judging PowerShell lines for every session. A session outside the
   five roles, the main session included, keeps its PowerShell tool. A Bash line that starts `pwsh -Command` is judged
   by the Bash rules as before. The personal reviewer's guard is out of scope (Q-B3-2).

## Consequences

No merge, approval or kit-code rule of a guarded role can be stepped around through the PowerShell tool (tested in
both layouts for each role, and for each installed guard directly). A Windows session of a guarded role uses Bash
`(verify: Bash is available to a Windows session of each role)`.

## Residual

- 2026-11-22: if the maintainers answer Q-B3-1 for reading PowerShell like Bash, each guard needs a PowerShell reader
  of its own rules (due 2027-01-31).

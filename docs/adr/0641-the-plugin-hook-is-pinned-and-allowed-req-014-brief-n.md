# ADR-0641: The plugin hook is pinned to LF, reads UTF-8 and is allowed by the distribution test (REQ-014)

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: brief #1518, issue #1517, SPEC-0005 rule 7, ADR-0612
- Requirements: REQ-014

Protected classes: `kit/`, `.claude/`, `tests/kit_dev/`

## Context

The default branch is red since #1498 (ADR-0612) merged at 4783e4d. Three kit tests fail: the installed gitattributes
does not pin `.claude/hooks/plugin_hooks.py` to LF; that hook's `subprocess.run(..., text=True)` reads `git` output
without `encoding="utf-8"`; and `test_ac2_plugin_ships_no_hook_server_monitor_bin_or_agent` still forbids the `hooks`
and `agents` keys of `.claude-plugin/plugin.json`, which ADR-0612 decision 1 added.

## Decision

1. `kit/templates/gitattributes` gains `.claude/hooks/plugin_hooks.py text eol=lf` after the `conductor_guard.py` line.
2. The `project_root` call of `subprocess.run` in `.claude/hooks/plugin_hooks.py` gains `encoding="utf-8"`; nothing
   else in the file changes.
3. The `plugin.json` key loop of the distribution test no longer forbids `hooks` and `agents` (ADR-0612 decision 1).
   The folder checks and the two-file `.claude-plugin/` check stay. A new assertion: every hook command of `plugin.json`
   runs `.claude/hooks/plugin_hooks.py`; a second command fails and the failure names it.
4. SPEC-0005 rule 7 is not edited here: the build proposes its one-line patch as Q-1518-1.

## Consequences

The default branch turns green. No behaviour a project runs changes, in any mode: a gitattributes line, one encoding
argument and a test change.

## Residual

SPEC-0005 rule 7 still says the plugin ships no hook until the maintainers answer Q-1518-1.

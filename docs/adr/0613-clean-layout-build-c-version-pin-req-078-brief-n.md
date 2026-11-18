# ADR-0613: Clean layout build (c): `[kit] plugin_version` pins one plugin version on every machine

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: brief #1455, SPEC-0071 rules 6, 10 and 12 (c), ADR-0611, Q-S0071-4, Q-S0071-7
- Requirements: REQ-078

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

SPEC-0071 rule 6 asks that a clean project (`[kit] layout = "plugin"`, ADR-0611) run on one plugin version on every
machine. Today nothing compares the plugin that runs with anything the project records, so two teammates on two
versions would both run, and a teammate with no plugin would fail with an error that does not say what to install.

## Decision

1. `[kit] plugin_version` in `agk.toml` pins the plugin. `kit_root.pin_refusal(root, plugin)` is the start check. In a
   clean project it refuses when the pin is missing or empty, when it differs from the top-level `version`
   (Q-S0071-7: the pin is added beside `version`, not instead of it), when no plugin runs the code, or when the
   running plugin's `version` in `.claude-plugin/plugin.json` differs from the pin, older or newer. The refusal is one
   line naming `plugin_version`, never a value. With no plugin it also names the one install command,
   `claude plugin install agk@agk` `(verify: the install command for a private source)` (Q-S0071-4). Outside a clean
   project it does nothing.
2. Where it runs. `common` runs it on import (`pin_gate`), so every kit script that imports `common` (108 of the 123
   under `scripts/agk/`) stops, exit 1, before any work. The running plugin is the one the file sits in. The project is
   the git top level of the working directory, found by walking up to `.git` without running git, so an offline
   machine and a second worktree behave the same. `kit_root.py`, which holds no `common` (a stub plugin carries it
   alone), runs the check itself after finding the plugin, before `--form`, the folder or the gate. The gate's checks
   then run from that plugin and check again. A session is covered by its first command (`doctor.py --paused`, which
   imports `common`). A hook that imports the kit's scripts is covered the same way. The hooks themselves, in
   `.claude/`, move to the plugin in build (b).
3. `config.TABLE_KEYS` names the `[kit]` table (`layout`, `plugin_version`), so the doctor's misplaced-settings warning
   names a pin written at the top level or in another table. `kit/templates/agk.toml` documents the table, commented
   out at the end of the file: `init` and `adopt` keep the installed layout, and only the migration of rule 8 writes it.
4. Raising the pin is a release pull request (SPEC-0028 rule 4), since the pin must equal `version`.

## Consequences

An installed project, the kit's own repository and personal mode are unchanged: with no `[kit] layout = "plugin"` the
check returns at once, and it reads only `agk.toml` and `.git`, so it adds no git call and no network to any script.
In a clean project a teammate on another version, or with no plugin, is stopped at the first command with the setting
to fix. The 13 other scripts under `scripts/agk/` that do not import `common` (such as `governance_map.py` and
`guard.py`) are not checked when one is run alone; that is left to a later build.

## Residual

- 2026-11-18: the install command for a private source stays `(verify)` until a run on a machine without the plugin
  reads it (due 2027-01-31).
- 2026-11-18: user-scope install for a second worktree stays `(verify)` on a real machine. The test proves only that
  the check finds the same plugin from a worktree (due 2027-01-31).

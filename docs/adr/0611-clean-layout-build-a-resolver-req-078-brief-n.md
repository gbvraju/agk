# ADR-0611: Clean layout build (a): one resolver runs the kit from the plugin or the repository

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1453, SPEC-0071 rules 2, 3 and 12 (a), ADR-0531
- Requirements: REQ-078

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `config/`, `agk.toml`

## Context

SPEC-0071 moves the kit into the plugin for a clean project (`[kit] layout = "plugin"`), in seven builds. Build (a)
gives every command one text for both layouts. A clean-install test stopped at `agk.mk is missing`, because `prepush.py`
and `evidence.py` find the governance gate only through the project's `agk.mk`.

The fact rule 2 marks `(verify: CLAUDE_PLUGIN_ROOT is set for every session, hook and headless job the plugin serves)`
was read by a recorded run before any change. The run was 2026-11-17T17:59:06Z, in a cloud scheduled session (entry
point `remote_cowork_trigger`). The AGK plugin was not installed there, and `CLAUDE_PLUGIN_ROOT` was unset in the session's
shell. So the run cannot confirm the fact for any case. It stays `(verify)` and is question Q-1453-1 on the pull request.
Nothing below depends on it: the variable is only the first place the resolver looks.

## Decision

1. `scripts/agk/kit_root.py` (new, standard library, installed) prints the folder of the kit's scripts for the project
   of the working directory (its git top level). With no `[kit]` table, or `layout = "installed"`, that is the project's
   own `scripts/agk/`, as today. With `layout = "plugin"` it is the plugin's `scripts/agk/`. The plugin root is
   `CLAUDE_PLUGIN_ROOT`, else the plugin the resolver itself sits in, and must hold `.claude-plugin/plugin.json` and the
   resolver, and differ from the project. With no such root, or another `layout`, it refuses with one line naming the
   setting (`CLAUDE_PLUGIN_ROOT` or `layout`), never a value, exit 1. It never writes into the plugin's folder.
2. `kit_root.py --form` prints the command prefix: `scripts/agk`, or `"${CLAUDE_PLUGIN_ROOT}/scripts/agk"` in a clean
   project. The session prompts (`kit/templates/runtime/builder.txt`, `conductor.txt`, `launcher.txt`) define `<kit>`
   once in one `KIT:` line and name each script as `python3 <kit>/<script>`. In an installed project `<kit>` is
   `scripts/agk`, so every command a session runs is the same text as before.
3. `config/session-rules.md` says once, in its opening paragraph, that a rule naming `python3 scripts/agk/<script>`
   means the resolver's plugin form in a clean project (SPEC-0071 rule 3). No numbered rule changes.
4. The gate. `kit_root.gate(root)` is today's `make -f agk.mk agk-governance` in an installed project (none when
   `agk.mk` is missing, so `prepush.py` gives today's refusal byte for byte). In a clean project it is
   `python3 <plugin>/scripts/agk/kit_root.py governance`, which runs `governance_map.CHECKS` (the commands of the
   `agk-governance` recipe, in its order, ADR-0531) from the plugin against the project's root, stopping at the first
   failure with its exit code. `prepush.py` and `evidence.py` run the gate this way. `evidence.py` accepts either form in
   a record.
5. Not in this build: the guards' allowed forms, the agents' and the skills' command forms, and the hooks. They are in
   `.claude/` and `skills/`, which the brief's `Touches:` does not name (Q-1453-2). Until they change, a clean project's
   guards allow only today's form. Because of that, and SPEC-0071's residual, the clean layout is not offered: no
   migration writes `layout = "plugin"` before build (d).

## Consequences

An installed project, the kit's own repository and personal mode behave as today. Each command form in the prompts gets
7 characters shorter. The one `KIT:` line adds more than that saves, so the prompts grow overall: builder 10041 to 10145
bytes, conductor 3222 to 3350, launcher 3383 to 3505. A clean project's gate needs no `agk.mk` and no `make`. The checks
themselves still read the project's `config/` and `constitution/`, which later builds handle.

## Residual

- 2026-11-17: `CLAUDE_PLUGIN_ROOT` for every session, hook and headless job remains `(verify)` until a run on a machine
  with the plugin installed reads it (Q-1453-1) (due 2027-01-31).

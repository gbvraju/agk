# ADR-0612: Clean layout build (b): the hooks, agents and permission rules run from the plugin

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: brief #1454, SPEC-0071 rules 4 and 12 (b), ADR-0611
- Requirements: REQ-078

Protected classes: `.claude/`, `.claude-plugin/`, `tests/kit/`, `kit/`

## Context

SPEC-0071 rule 4 marks three facts `(verify)` and says a recorded run settles each before build (b) changes anything.
The runs were made on 2026-11-18 from 01:29Z to 01:37Z, in a cloud scheduled session, with Claude Code 2.1.327 run
headless (`claude -p`). The model was a stub: a Messages API on `127.0.0.1` that asks for one Bash call, then ends. No
model and no network outside the machine. The plugin was a stub with its own `.claude-plugin/plugin.json`, loaded with
`--plugin-dir`, and once installed at user scope from a local directory marketplace; then this repository itself, loaded
with `--plugin-dir`. Each project was a git repository of invented data; a worktree was named `cb-example-1`.

What the runs showed, for this version of Claude Code:

1. **Plugin hooks fire in every session.** A `SessionStart` and a `PreToolUse` hook declared in `plugin.json` fired in a
   headless session, with and without `--agent`, and in a git worktree with the plugin installed at user scope (no
   `--plugin-dir`). In each, the hook's environment had `CLAUDE_PLUGIN_ROOT` (the plugin's folder) and
   `CLAUDE_PROJECT_DIR` (the project, or the worktree). The hook's input carries `agent_type` (`agk:conductor`) when the
   session runs an agent.
2. **A plugin agent is named `<plugin>:<name>`.** `--agent agk:conductor` ran the plugin's agent: its prompt and only its
   `tools:`. With no project agent of that name, `--agent conductor` ran it too. An agent file listed in `plugin.json`'s
   `agents` is loaded; the list replaces the default `agents/` folder. **A plugin agent's own frontmatter `hooks` do not
   fire**: the agent's `PreToolUse` hook wrote nothing while the plugin's hook wrote its line.
3. **A plugin cannot carry a permission rule, and a rule names a plugin path only by its absolute path.** An `allow`
   rule in the plugin's `settings.json` was not applied. In a trusted project, `.claude/settings.json` and
   `--allowedTools` applied `Bash(python3 <absolute plugin folder>/scripts/agk/*)`. A rule that names
   `${CLAUDE_PLUGIN_ROOT}` matched nothing, and a command that names the variable was held for approval ("a variable in
   braces ... can't be checked before it runs"). A leading wildcard (`Bash(python3 */scripts/agk/hello.py *)`) also
   allowed the same script name in another folder.
4. **The Bash tool's shell has no `CLAUDE_PLUGIN_ROOT`** (`printenv CLAUDE_PLUGIN_ROOT` exits 1), so a prompt's command
   cannot name the variable (Q-1453-1, for the headless shell).
5. **The guards fire from the plugin in a clean project.** With this repository as the plugin, in a project whose
   `agk.toml` has `[kit] layout = "plugin"` and no `.claude/`, `cat .env` was refused by the data guard
   (`data guard: secret-file (env file): ...`) and the Stop hook ran the stop check.

## Decision

1. `.claude-plugin/plugin.json` registers two plugin hooks, `PreToolUse` (the data guard's matcher, timeout and
   `onFailure`) and `Stop`, both running `.claude/hooks/plugin_hooks.py` from the plugin. It lists the six agents of
   `kit/manifest.json` in `agents`, so they are `agk:architect`, `agk:architect-review`, `agk:conductor`,
   `agk:drift-auditor`, `agk:shadow` and `agk:steward`.
2. `plugin_hooks.py` (new, standard library, a verbatim file of the manifest) runs the plugin's own guard with the hook's
   input and passes its output and exit code back unchanged. The data guard and the stop check run only for a project
   that does not register them itself: `[kit] layout = "plugin"`, or an `agk.toml` with no own copy of the guard. An
   installed project, the kit's own repository and a project with no `agk.toml` keep `.claude/settings.json`, so no
   guard runs twice. Because a plugin agent's frontmatter hooks do not fire (fact 2), it also runs the agent's guard
   whenever `agent_type` names one of the five guarded plugin agents, in either layout, on the agents' matcher
   (`Edit|Write|MultiEdit|NotebookEdit|Bash`). Input it cannot read, or a guard it cannot start, denies.
3. `stop_check.py` runs the gate of `kit_root.gate` and the map's scripts from the plugin in a clean project. An
   installed project runs `make -f agk.mk agk-governance` as today.
4. Permission rules: by fact 3 the plugin cannot carry them, and a project rule that names the plugin must name its
   absolute folder, which differs on each machine. A committed project `.claude/settings.json` of plugin paths
   (`Q-S0071-6`) therefore cannot be written as the same text for every machine. This build writes none; Q-1454-1 asks
   the maintainers for the form before build (d) writes one.
5. Not in this build: the guards' allowed command forms. In a clean project the conductor's and the architect's guards
   still allow only today's `scripts/agk/` forms and the project's own files, so they refuse the plugin's form: they
   fail closed (Q-1454-2). The clean layout stays not offered (SPEC-0071 residual).

## Consequences

The data guard, the stop check and the agents' guards run from the plugin in a clean project, and the data guard refuses
there exactly as in an installed one (tested for every built-in secret shape). An installed project and the kit's own
repository run their hooks as today; with the plugin installed, a session there that names `agk:conductor` (or another
guarded plugin agent) gets that agent's guard from the plugin, which it would not get from the agent file alone.

## Residual

- 2026-11-18: the facts above hold for Claude Code 2.1.327 headless; an interactive session and a Windows machine were
  not run (due 2027-01-31).
- 2026-11-18: the form of a clean project's permission rules is open (Q-1454-1) (due 2027-01-31).

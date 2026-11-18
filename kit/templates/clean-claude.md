# CLAUDE.md: {{project}} (the AGK clean layout)

This project runs AGK from the plugin, not from files in this repository (SPEC-0071 rule 2). The plugin's
version is pinned: `[kit] plugin_version = "{{kit_version}}"` in `agk.toml`. Every kit script refuses at start,
naming `plugin_version`, when another plugin version runs, or none.

Read first, from the plugin's folder `${CLAUDE_PLUGIN_ROOT}`:

1. `${CLAUDE_PLUGIN_ROOT}/constitution/principles.md`, the twelve rules, authoritative.
2. `${CLAUDE_PLUGIN_ROOT}/config/core-rules.md` and `${CLAUDE_PLUGIN_ROOT}/config/session-rules.md`.

Run a kit script as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/<script>"` from this project's root; the gate is
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/kit_root.py" governance`. Never copy a file of the plugin into this
repository.

This repository keeps only the project: `agk.toml`, its requirements, specs, ADRs, build state, run records,
briefs, vision and design documents, its own code and tests, `.gitignore` and the issue and pull request
templates.

## The project's own rules

Add this project's own rules below, one numbered line each.

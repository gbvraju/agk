# ADR-0637: Personal mode records its plugin version, upgrades one step at a time and detaches with its hook

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: ADR-0267, ADR-0634, SPEC-0041, brief #1506
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0041 rule 26 asks that personal mode runs from the user-scope plugin, that the sidecar stores the plugin version
and never a script, and that `doctor.py` on a sidecar reports each pinned copy that differs from `kit/hashes.json` for
that version. Rule 27 asks for an upgrade of `[personal] schema` one step and one sidecar commit at a time, and a
`detach` that removes the opt-in hook only when it is unedited; rule 19 asks for that opt-in `pre-push` hook, the one
write under the clone's `.git/`. On main the sidecar recorded no version, `doctor.py` printed the mode line alone, and
there was no `upgrade` and no hook. ADR-0267 asks each build of the spec for its own ADR naming its classes; this is
build (l).

## Decision

1. `personal_state.py attach` writes `[personal] plugin_version`, read from the plugin's `.claude-plugin/plugin.json`;
   `common.PERSONAL_KEYS` accepts the key and `common.PERSONAL_PINNED` names the four pinned files that `attach`
   copies. `doctor.py` on a sidecar prints the mode line, then `pinned: 4 files match kit/hashes.json` or one line per
   missing or differing copy (its bytes as they are and with CRLF read as LF), or `pinned: not checked` naming
   `personal.plugin_version` or `kit/`, never the version or the text; on Windows it adds that the permissions were
   not checked (rule 28). A difference is reported and the exit stays 0 (Q-1506-3).
2. `personal.py upgrade [--clone DIR] [--sidecar DIR]` raises `[personal] schema` from the sidecar's to
   `personal_state.PLUGIN_SCHEMA` (1 on this release) through `personal_state.MIGRATIONS`, one sidecar commit per step
   holding `agk.toml` and the step's own paths. It refuses a schema newer than the plugin's, a sidecar with uncommitted
   changes and a missing step, each naming the setting or path class.
3. `personal.py hook install [--clone DIR]` writes `<git common dir>/hooks/pre-push`, untracked and executable, which
   runs `python3 <plugin>/scripts/agk/personal.py gate --clone . --approve` and fails closed with one line when that
   path is gone. It refuses with `core.hooksPath` set, over an existing `pre-push`, and on a clone with no sidecar.
   `hook remove` removes it only when its bytes equal what `install` writes for the plugin path it records, so no
   state is kept for it.
4. `personal_state.py detach` prints the export line first, removes the registry entry (and, with `--delete-state`,
   the state after the typed id), then removes the kit's hook when unedited, or says it was changed by hand and leaves
   it; a `pre-push` without the kit's mark is left and not named.
5. `tests/kit/test_personal_lifecycle.py` walks one sidecar through attach, survey, the gate, report, upgrade and
   detach and checks that the clone's status stays empty and every file under its `.git/` keeps its path, size and
   SHA-256. `agk.toml` maps `personal.py`, `personal_state.py`, `doctor.py` and `common.py` to it.

## Consequences

A plugin upgrade can now tell a sidecar's pinned copies apart from its own, and a later schema adds one entry to
`MIGRATIONS`. The hook is the only file personal mode writes under `.git/`, and only when the person asks for it.

## Residual

- 2026-11-20: the plugin command `/agk:personal push` is not added here (Q-1506-2); `personal.py gate` is what it runs.
- 2026-11-20: the personal-mode guide with the install line is build (n); the reference names the line, marked
  `(verify: the install command and scope flag)`.

# ADR-0614: Clean layout build (d): `/agk:upgrade --clean-repo` moves a local-mode project in one reversible pull request

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: brief #1456, SPEC-0071 rules 2, 8, 11 and 12 (d), ADR-0611, ADR-0612, ADR-0613, ADR-0203, Q-S0071-5, Q-S0071-8
- Requirements: REQ-078

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `skills/`, `agk.toml`

## Context

SPEC-0071 rule 8 asks for one command that moves an installed project to the clean layout (`[kit] layout =
"plugin"`, ADR-0611) as one pull request that a revert undoes. Builds (a) to (c) made the kit run from the plugin
and pinned its version (ADR-0613), but nothing writes the `[kit]` table or removes the installed kit files.

## Decision

1. `upgrade.py TARGET --clean-repo [--rehearsal] [--write]` (kit-only, run from the plugin) is the migration;
   `/agk:upgrade` documents it. A dry run is the default and writes nothing.
2. It refuses, with one line naming the setting or the path class and never a value, in this order: a `[personal]`
   table (personal mode, setting `forge`); `execution` other than `local` (absent is `hosted`); until build (g)
   writes the rehearsal's four figures (rule 11) unless `--rehearsal`, naming that proof; a `version` with no row
   of the plugin's `kit/hashes.json` (path class `kit/hashes.json`); a `version` other than the plugin's, since the
   pin must equal both (ADR-0613; setting `version`: upgrade first); an existing `[kit]` table (setting `layout`).
   Until build (g), `CLEAN_PROOF_HELD` in `upgrade.py` is false, so only `--rehearsal` runs; the script cannot tell
   a sample from a customer project, so the flag is the person's statement.
3. What it removes: every path that the manifest's `verbatim` list or any release row of the table names (the
   table's full history), except the kit-only paths and rule 2's files (`.gitignore`, `LICENSE-AGK`, the issue
   and pull request templates, `agk.toml`; `CLAUDE.md` is rewritten as decision 4 says), held in one list,
   `upgrade.CLEAN_KEPT`, that other scripts import, and the project's own work as `uninstall.py` reads it. Each is matched as `uninstall.py`
   matches it (`classify`): a released copy is deleted, a marked agk block is taken out of a file with the
   project's own lines, and a file that differs from every released copy is listed as `changed` and kept, named
   for the pull request body (Q-S0071-8). `include agk.mk` leaves a kept `Makefile`.
4. What it writes: the short `CLAUDE.md` from `kit/templates/clean-claude.md` (22 lines; the project's lines after
   an agk block are kept below it; a changed `CLAUDE.md` is kept instead), and `[kit] layout = "plugin"` and
   `plugin_version` equal to `version`, appended last to `agk.toml`. As ADR-0612 decision 4 settled, the plugin's
   permission rules, naming this machine's plugin folder, go to the uncommitted `.claude/settings.local.json`, and
   only when that file does not exist. It writes this migration's own ADR, Proposed, naming the protected classes
   it changes, as `--write-adr` does for an upgrade.
5. The proof: before anything is written, every tracked text file that remains, read with its planned content, is
   scanned for a removed file or a folder that the removal empties, with the paths of `${CLAUDE_PLUGIN_ROOT}`
   excepted. The folders of the project's own records (`uninstall.OWN_DIRS`) are not removed folders. A finding
   is printed as `<file>:<line>` with its path class, at most 40 lines. The run then refuses, naming the classes,
   and writes nothing.
6. `--write` makes the branch `agk-clean-repo` with `uninstall.py`'s `new_branch`, which refuses a work tree with
   changes or an existing branch, writes there and commits nothing. The person commits it as one commit, so
   reverting that commit undoes the move. It raises no `version`.

## Consequences

An installed project, CI mode, personal mode and the kit's own repository are unchanged: the plain upgrade runs as
before, and the migration refuses outside local mode, in a sidecar and inside the kit checkout. A fresh install
does not pass the proof as it is. Its rendered settings (`config/protected-paths.txt`, `config/reviewers.yaml`, the
comments of `agk.toml`, `.gitattributes`) and records (`docs/adr/0001-adopt-agk.md`, `docs/runs/flakes.md`) name kit
paths, so the person tidies them before the move (Q-1456-1). Once committed, the migration's own ADR names the
classes it removed.

## Residual

- 2026-11-18: each other machine of the project needs the plugin's permission rules in its own
  `.claude/settings.local.json`; this build writes them only on the machine that runs the migration (due 2027-01-31).
- 2026-11-18: whether records under `docs/adr/` and `docs/runs/` are exempt from the proof is Q-1456-1 (due 2027-01-31).

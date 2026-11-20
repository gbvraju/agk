# ADR-0615: Clean layout build (e): `/agk:uninstall` in a clean project removes the licence and the agreed records and prints the history clean-up

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: brief #1457, SPEC-0071 rules 9 and 12 (e), ADR-0203, ADR-0604, ADR-0614, Q-S0071-1, Q-S0071-9, Q-1457-1
- Requirements: REQ-078

Protected classes: `scripts/agk/`, `tests/kit/`, `skills/`, `agk.toml`

## Context

SPEC-0071 rule 9 asks that `/agk:uninstall` end an engagement in a clean project (`[kit] layout = "plugin"`,
written by build (d), ADR-0614) with one pull request that removes `LICENSE-AGK` and the records the owner and
the customer agreed to remove, keeps the specs and decisions by default, and prints, never runs, a history
clean-up of every kit path the project's history holds, with a checklist. `uninstall.py` (ADR-0203) removes an
installed kit, but in a clean project it kept the licence (a clean project's own file) and the short
`CLAUDE.md` (no released copy), and it printed nothing about the history.

## Decision

1. `uninstall.py` reads the clean layout from `agk.toml` (`[kit] layout = "plugin"`). An installed project is
   read as before (Q-S0071-9): no decision of ADR-0203 or ADR-0604 changes there.
2. In a clean project the plan also deletes `LICENSE-AGK`, whatever its content, and the short `CLAUDE.md` that
   `kit/templates/clean-claude.md` renders for the project's folder name and `plugin_version`; when the
   project added its own lines below it, only the short part goes. A `CLAUDE.md` that does not start with it is
   listed as `changed` and kept, as before.
3. The agreed records are named by the person, one `--agreed PATH` (a file or a folder) each. A path must name an
   existing file or folder of the project's own records as `own_work` reads them (requirements, ADRs, specs,
   briefs, the vision, design documents, `docs/runs/`, `docs/build-state.md`); anything else, a path outside the
   project or through a symlink, or a path that matches nothing is refused, naming `--agreed` and never the
   path. Nothing else of the records is deleted, so the specs (`docs/specs/`) and decisions (`docs/adr/`) stay
   unless named (Q-S0071-1). `--agreed` in an installed project is refused naming `layout`, and with `--pause`
   it is a usage error.
4. The history clean-up is the set of every path of every release row of the plugin's `kit/hashes.json` (its
   `verbatim`, `blocks` and `templates` keys) that `git log --all -m --no-renames --name-only` names, less the
   project's own work. It is printed one `history path:` line each, with the `git filter-repo --invert-paths
   --paths-from-file` command `(verify: the git filter-repo options for a path list)`, a line naming the listed
   paths that also hold the project's own lines (the block files), and the checklist: the customer's choice to
   clean the history where its audit and retention policy allows or else keep it and record the decision, the
   customer's written agreement, branch protections paused and restored by the repository's administrator, and
   every clone made again. The script runs only read-only `git` for it.
5. `--write` makes the one branch `agk-uninstall` and commits nothing, as before. The script never runs `git
   filter-repo`, never pushes and never calls `gh`.

## Consequences

The customer ends an engagement with one reviewable pull request and a printed, complete list for its own
history decision. A record the owner and the customer agreed to remove is named on the command line, so the
agreement stays the person's and the tool deletes no record by its own reading.

## Residual

- 2026-11-19: the `git filter-repo` command form is marked `(verify)` until a recorded run settles it (due 2027-01-31).
- 2026-11-19: a short `CLAUDE.md` rendered for another folder name, in a clone under another name, is listed as
  `changed` and kept for the person to delete (Q-1457-1) (due 2027-01-31).

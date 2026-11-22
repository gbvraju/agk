# ADR-0694: The bill of materials and the steward's skill lookup read the plugin's files in a clean project

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1667, SPEC-0054, SPEC-0059, SPEC-0071, ADR-0683, ADR-0611, plan #661
- Requirements: REQ-078

## Context

A clean-layout project (`[kit] layout = "plugin"`, ADR-0683 decision 1) holds no `config/ci-tools.txt` and no
`.claude/agents/steward.md`. Measured on main at 483ecfcf (2026-11-21): in a project made by
`init.py --layout plugin --rehearsal`, `sbom.py make` failed `FAIL bom: config/ci-tools.txt cannot be read at the
commit (rule 2)`, and `steward_evidence.py skill --step start` printed `refused: [Errno 2] No such file or directory`
with the role file's full path (exit 2).

## Decision

1. `sbom.py` reads `[kit] layout` from `agk.toml` at the commit it describes, as it reads every other file. With
   `plugin` the bill lists the product's own components only: its Python dependencies, its own workflows and its
   committed stack lock. The kit's CI tool pins and kit files belong to the plugin and are left out, even when a stray
   copy is committed, and a missing `config/ci-tools.txt` is no failure. With `installed` or no `[kit]` table the bill
   is as before (the kit's own bill at 483ecfcf is the same, byte for byte). Another value is refused with one line
   naming the setting `layout`, the refusal `kit_root.layout` gives.
2. `steward_evidence.py` reads the role file from the project when it can be read, else, in a clean project, from
   `kit_root.plugin_root`'s `.claude/agents/steward.md`. When neither can be read it refuses one line naming the path
   class `.claude/agents/` (exit 2). `kit_root`'s own refusals (no plugin, setting `CLAUDE_PLUGIN_ROOT`; another layout,
   setting `layout`) print as the same one `refused:` line, never a traceback. The pin check of `plugin_version` stays
   where it is: in `common` on import (ADR-0613).

Protected path classes changed: `scripts/agk/` (`sbom.py`, `steward_evidence.py`) and `tests/kit/`
(`test_sbom_clean.py`, `test_steward_evidence_clean.py`).

## Consequences

The prepush `bom` step and the steward's first lookup of every step work in a clean project. `kit_root.plugin_root`
falls back to the plugin the script runs from when `CLAUDE_PLUGIN_ROOT` names a folder that is not a plugin, so that
variable is refused only when no plugin is found at all; this ADR keeps that behaviour.

## Residual

- 2026-11-21: none.

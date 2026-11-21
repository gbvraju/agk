# ADR-0697: A clean-layout project reads its playbook from the plugin

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1666, SPEC-0071, ADR-0683, ADR-0611, ADR-0666, plan #661
- Requirements: REQ-078

## Context

A clean-layout project (`[kit] layout = "plugin"`) carries no `config/playbooks/` (ADR-0683 decision 1), but every
playbook reader joined the project's root with that folder. Read on main at 483ecfcf (2026-11-21): a declared work
type failed `rule 5` for a missing file, and with none declared `run_gates.py` printed `ok gates (no check gate)`, the
`layers` step passed a forbidden import and `check_plan.py` skipped its work-type rules.

## Decision

1. One resolver in `playbook_format.py`: `folder(root, name)`, `path(root, name)` and `default_playbook(root)`. In the
   installed layout the folder is the project's `config/playbooks/`, as before; in a clean one it is the project's
   when it holds `<name>.toml`, else the plugin's (`kit_root.plugin_root`). The declaration check, `selected`,
   `split`, the modules, `check_playbooks.py`'s composition, `run_gates.playbook`, `gates/layers.py`,
   `gates/python_pack.py` and `engines.py` read through it. A partial copy of the scripts without `kit_root.py` reads
   the project's folder alone.
2. A refused `[kit] layout` or a missing plugin root is the declaration's problem, naming `layout` or
   `CLAUDE_PLUGIN_ROOT`, never a value.
3. No silent pass: with no playbook found, `run_gates.py` fails one line naming `work_type` (or the path class
   `config/playbooks/` when none is declared); `check_plan.py` prints `not run plan work-type rules: <reason>` and
   never `ok plan`. An installed project that declares nothing and carries no playbook keeps today's output, so the
   kit's own repository and the installed layout are unchanged.
4. `check_playbooks.py` checks the project's own playbooks, as today, plus the plugin's file the declaration selects.

Protected path classes changed: `scripts/agk/` (`playbook_format.py`, `run_gates.py`, `check_playbooks.py`,
`check_plan.py`, `engines.py`, `gates/layers.py`, `gates/python_pack.py`) and `tests/kit/` (`test_playbook_plugin.py`).

## Consequences

A clean project runs the gates, layers, standards pack and plan rules of its declared work type from the plugin it
pins, and a project's own file of a name still wins. `check_plan.py`'s `not run` line exits 0: the failure of the
declaration is `check_playbooks.py`'s, so governance still fails once.

## Residual

- 2026-11-21: `steward_owner.py standard` and the other readers that call `selected` follow the resolver with no test of
  their own here; the brief's `Touches:` names only the readers it tests (due 2027-01-31).

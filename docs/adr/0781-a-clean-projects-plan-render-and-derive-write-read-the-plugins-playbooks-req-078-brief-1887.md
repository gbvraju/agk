# ADR-0781: A clean project's plan render and derive-write read the plugin's playbooks (REQ-078)

- Status: Accepted
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1887, ADR-0697 (the playbook resolver of brief #1666), ADR-0759 (the kit's own files from the plugin
  and the guard test of brief #1826), ADR-0683 (new and adopted projects start clean), ADR-0461 (render writes drafts
  once), ADR-0312 (the work-type declaration), plan #661
- Requirements: REQ-078

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

A clean project (`[kit] layout = "plugin"`) holds no `config/playbooks/`: every shipped playbook is the plugin's, and
`playbook_format.folder`, `path`, `default_playbook` and `selected` resolve it (ADR-0697). Two readers still assumed the
file sits under the project root. Test plan 2 run PB-07: `plan_intake.milestone_order` printed
`path.relative_to(root)` on the plugin's file, so `render` with a design's screens ended in a `ValueError` and wrote
nothing. Test plan 3 run AD-05: `front_door.derive_write` read `root / config/playbooks/default.toml` and refused
`rule 22: config/playbooks/default.toml: missing or not sound`. Both reproduced on main at 9482f54 (the brief's
`Measured:` line). The guard of ADR-0759, `tests/kit_dev/test_kit_paths_resolved.py`, missed both: it read only the
module's own constants, skipped folders and never looked at `relative_to`. The owner's word (2026-11-24, the steward
chat, quoted as data): "Yes, draft the test briefs and post the runs".

## Decision

1. `plan_intake.milestone_order` names the playbook as `config/playbooks/<file name>`, never by `relative_to`: the
   installed layout and a clean project's own file give the same text as before, and the plugin's file gives that same
   path class, never the plugin's folder (`Q-PP-1`).
2. `front_door.derive_write` refuses a `[kit] layout` outside `installed` and `plugin` by
   `playbook_format.layout_problem`, naming `setting: layout`, then reads its base by
   `playbook_format.default_playbook`: the project's own `default.toml` when it holds one, else the plugin's. None, or
   a file `playbook_format.problems` refuses, keeps the line `rule 22: config/playbooks/default.toml: missing or not
   sound`. The derived file is still the project's `config/playbooks/<slug>.toml`; the folders made for it are removed
   with it when the check refuses it, so a refusal writes nothing. `steward_owner.py`'s draft follows with no change.
3. The guard learns three forms: a string constant of another kit module (`playbook_format.FOLDER`); a kit-only
   folder, one that holds a kit-only file and whose every file in the kit's tree is one (`config/playbooks/`), as a
   match for any join whose known leading parts name it or lie in it; and `.relative_to(<root name>)` on what
   `playbook_format.selected`, `path`, `folder`, `default_playbook` or `kit_root.kit_file` returns, directly or through
   a name the function binds to it. New `ALLOWED` rows with their reasons: `playbook_format.folder` and `path` (`the
   resolver`), `playbook_format.playbooks` and `steward_owner.composed_standard` (`the project's own file`), and three
   the folder form also finds: `.claude/hooks/plugin_hooks.project_runs_own` and `check_runbooks.cmd_check`
   (`installed layout only`) and `uninstall.own_files` (`the project's own file`) (`Q-1887-1`).
4. This repository's `[testing] map` lists `tests/kit/test_plan_intake_clean.py` for `scripts/agk/plan_intake.py` and
   `tests/kit/test_front_door_derive.py` for `scripts/agk/front_door.py`.

## Consequences

A clean project renders its plan and drafts a derived playbook with the plugin's playbooks and no hand copy. An installed
project reads `config/playbooks/` as before, with the same output and refusals. A kit script that reads a kit-only
folder at a project path, or makes a project-relative path of a resolver's result, now fails the guard in review.

## Residual

- 2026-11-24: agent and skill prose that tells an agent to read `config/playbooks/<work type>.toml` is out of scope
  (`Q-PP-2`); `docs/plan/prototype-coverage.md` has no writer and is out of scope (`Q-PP-3`).

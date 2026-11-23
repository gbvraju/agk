# ADR-0759: A clean project reads the kit's own files from the plugin (REQ-078)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1826, ADR-0456, ADR-0503, ADR-0611, ADR-0612, briefs #1665, #1666, #1667, plan #661
- Requirements: REQ-078, REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

A clean project (`[kit] layout = "plugin"`, SPEC-0071 rule 2) holds only `upgrade.CLEAN_KEPT` and its rendered
records; the kit's scripts, hooks, templates, principles and stack table are the plugin's. `plan_intake.guard_missing`
checked `scripts/agk/guard.py` and `.claude/hooks/data_guard.py` under the project root (SPEC-0043 rule 3, ADR-0456
decision 1), so every `plan_intake.py` command printed `data guard not installed: scripts/agk/guard.py`, exit 2, in a
clean project, although the plugin's guard runs there through `plugin_hooks.py`. `new_spec.py` refused `cannot read
the template`, `review_context.assemble` reported the principles missing and `playbook_format.stacks` skipped the
stack check, for the same cause. `kit_root` resolved only the scripts folder; each earlier fix (briefs #1665, #1666,
#1667) wrote its own lookup. The owner's word (2026-11-23, the steward chat, quoted as data): "Yes, brief the four
blockers".

## Decision

1. `kit_root.kit_file(root, rel, env=None)` is the one resolver of a kit file: `root / rel` in the installed layout,
   `plugin_root(root, env) / rel` in a clean one, never the project's own copy there. It never writes, and refuses as
   `layout` (naming `layout`) and `plugin_root` (naming `CLAUDE_PLUGIN_ROOT`) do.
2. SPEC-0043 rule 3's two paths are read as kit files found by that resolver (Q-1826-1). In the installed layout the
   gate checks the project's two files exactly as before (ADR-0456 decision 1). In a clean one it checks the plugin's
   `scripts/agk/guard.py`, `.claude/hooks/data_guard.py` and `.claude/hooks/plugin_hooks.py`; a missing one prints
   `data guard not installed: ${CLAUDE_PLUGIN_ROOT}/<rel> (setting: [kit] layout)`, exit 2, never an absolute path.
   The condition stays whether it is installed, never a setting that turns it off. Another `[kit] layout` exits 1
   naming `layout`.
3. `plan_intake.cmd_render`'s spec template check, `review_context.assemble`'s principles and
   `playbook_format.stacks` read through `kit_file`. `new_spec.py` keeps ADR-0503 (standard library only, no kit
   module): it reads `[kit] layout` with `tomllib` and, for `plugin`, the template of the kit tree it sits in; a test
   holds its path equal to `kit_file`'s. The refusals keep their wording.
4. `tests/kit_dev/test_kit_paths_resolved.py` parses every `.py` under `scripts/agk/` and `.claude/hooks/` and fails
   on a `/` join or a call that puts a kit-only path (a manifest `verbatim` or `snapshot` file outside `CLEAN_KEPT` and
   the rendered records) beside a project root name outside the resolvers. Its allow list names each remaining site
   with its file, function and reason; a stale row fails, so the list only shrinks. `session.rule_texts` and
   `session.body_lines` stay as rows marked `open` for their own brief (Q-1826-4).
5. Path classes changed: `scripts/agk/` (`kit_root.py`, `plan_intake.py`, `new_spec.py`, `review_context.py`,
   `playbook_format.py`), `tests/kit/` (`test_kit_root.py`, the new `test_plan_intake_clean.py`) and `tests/kit_dev/`
   (`test_new_spec.py`, the new `test_kit_paths_resolved.py`). No setting is added; `execution`, `review_mode`,
   `pr_mode`, `[guard]` and personal mode read the same lookup, and a clean project is `local` and never personal.

## Consequences

`/agk:plan-intake`, `/agk:spec`, `/agk:brief` and `/agk:review` run in a clean project as in an installed one, and
`check_playbooks.py` checks `[[standards]]` stacks against the plugin's table. An installed project, the kit's own
repository included, is gated and read exactly as before. A clean project's own copy of a kit file is not read
(Q-1826-2); `doctor.py` warns `kit-in-repository` as before.

## Residual

`session.py prompt` for a builder still reads `config/session-rules.md` and `config/core-rules.md` from the project and
fails in a clean project (Q-1826-4, its own brief). SPEC-0043 rule 3's text still names the two paths as project paths;
an amendment is the reviewers' to propose (Q-1826-1).

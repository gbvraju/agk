# ADR-0857: A project brief names what already exists, and review asks whether a change rebuilds it

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2065, 2026-11-27T19:30:39Z)
- Related: ADR-0850, ADR-0752, ADR-0756, ADR-0757, ADR-0758, ADR-0759, ADR-0669, ADR-0310, ADR-0294, SPEC-0023,
  SPEC-0030, SPEC-0076, REQ-037, brief #2052, brief #2065, plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `skills/`, `config/`, `.claude/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

ADR-0850 (brief #2052) holds a kit brief to one `Existing:` line and searches the kit's scripts for what the brief
names; its answer 3 (`Q-P0A-1`) leaves a project root (no `kit/agk-kit.mk`) out "until an ADR extends it". This is that
ADR. A project brief can still propose what the project's own code, a dependency or a kit feature already does: the
portal's pull request #27 (2026-10-22) was rejected at review because it rebuilt the report's logic in a second
language, caught by hand after the build was planned (`docs/runs/architect-catches-3.md`, row 1). The review lens
names only logic copied from a kit file, and checklist item 10 only a workaround of a kit gap.

## Decision

1. **The line in a project brief.** Without `kit/agk-kit.mk`, a brief is held to the same `Existing:` line in the same
   two forms, read by `brief_study.existing_problems`. An item that names no `<path>:<line>` is accepted in a project
   when it names a kit command or kit path in backquotes (a kit feature in the plugin layout has no file under the
   root, `Q-P0AP-2`); a `<path>:<line>` it does name is checked under the root. The kit's root reads as ADR-0850 says.
   Breaks warn before the project's own `[flow] brief_study_fails_from` and fail from it (`enforced`, unchanged); the
   placeholder warns on any day; a `Priority: 0` brief is not held. `kit/templates/agk.toml` is left as it is: a
   project never fails until it sets its own day (`Q-P0AP-3`).
2. **The project's source.** `brief_study.project_source(root)` is the files `config.project_lint_paths` names when it
   is set; else the tracked files (`pins.tracked`) whose extension is a `survey.LANGUAGES` key, less `NOT_CODE`, the
   project's `test_dirs`, the `ignore` folders of `config/stack-signals.toml`, `check_licence_notice.KIT_FOLDERS`,
   `config/`, `constitution/`, `.github/` and each file `survey.detect_test_files` names. At most `SOURCE_FILES = 2000`
   files under `survey.TOO_LARGE` bytes are read; the rest are counted by `brief_study.py` as `code search: <n> files
   not read`. A refused `project_lint_paths` runs no code search (`not run code search: ... (setting:
   project_lint_paths)`).
3. **The search in a project, warnings only.** `code_matches` searches the project's source, then the kit's scripts
   (`kit_root.kit_dir`), the kit's `docs/guides/reference.md` (`kit_root.kit_file`), the ids of `packs.used` and the
   direct dependencies of each `pins.STACKS` build file at the root (or the `Part` column of `docs/parts.md` when
   present). Two term classes join ADR-0850's three: a source file by name and a part. A non-Python declaration is read
   by `brief_study.declares`. A match `Existing:` leaves out is warned as `defines`, `declares` (a part) or `documents`
   (a kit command), sharing `CODE_WARNINGS`. A kit copy that cannot be resolved, or a refused `[packs]` table, leaves
   that layer out with one `not run ...` line naming the setting. Files only: no network, no model.
4. **Review asks it.** Checklist item 10 (`kit-defect`) is widened to a rebuild of what the project's code, a part or a
   kit feature already does, citing catch-log row 1 of `docs/runs/architect-catches-3.md` (SPEC-0023 rule 5): no new
   question and no new kind (`Q-P0AP-6`). The lens's last entry in the four protocol copies reads `duplication (logic
   copied from a kit file, or rebuilt where the project's code, a part or a kit feature already does it)`; the words
   it adds are cut in the same protocol block, and no baseline of `config/rule-budget.txt` rises.
5. **Left as they are.** `steward_evidence.SOURCES`, `front_door.detect_facts` and SPEC-0076's parts record
   (`Q-P0AP-4`, `Q-P0AP-7`); a project's own file under `scripts/agk/` is read as the kit's (`Q-P0AP-5`).

## Consequences

- A project brief that rebuilds its own code, a dependency or a kit feature is warned on the draft, and every
  verdict's `Checklist:` line for item 10 asks for it.
- A project that already set `[flow] brief_study_fails_from` fails a brief filed after it upgrades when the line is
  missing; the changelog line says so.
- One `git ls-files` and at most 2000 file reads per project brief check with `--root`.
- The project-tree fixtures of the brief tests (`tests/kit/` and one in `tests/kit_dev/`) carry an `Existing:` line,
  and ADR-0850's test that a project reads no line now asserts the kit's reading for a project tree.

## Residual

The signal of use is read by hand on a project after it upgrades (the brief's `Measured:` line): the share of its
`agk-brief` issues created after the upgrade day that carry an `Existing:` line, and the count of `warning: study:
Existing` lines in its brief-check comments, reported after its first five briefs (2027-01-31). A module inventory in
`front_door.detect_facts` and SPEC-0076's builds stay open questions (`Q-P0AP-4`, `Q-P0AP-7`).

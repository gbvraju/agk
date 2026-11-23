# ADR-0767: An adopted project gets layers drafted from its tree; a layer set that holds no file and an unfilled record fail (REQ-079)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: SPEC-0072 rules 5, 7, 8 and 9, SPEC-0038 rule 5, SPEC-0048 rule 22, ADR-0668, ADR-0675, ADR-0680, ADR-0681, ADR-0697, brief #1842, brief #1829, plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (`gates/layers.py`, `run_gates.py`, `front_door.py`,
`steward_owner.py`), `skills/` (`adopt/SKILL.md`) and `tests/kit/` (`test_layers_draft.py`, `test_layers_step.py`,
`test_architecture_record.py`, `test_front_door_derive.py`, `test_standard_confirm.py`). The repository's own
`agk.toml` gains three `[testing] map` entries for the new test file (ruled on #1846). `kit/hashes.json` is not edited
by hand.

## Context

On main at e13f4f53 an adopted Python service whose folders match none of the work type's layers passed `ok layers`
and `ok architecture-record`: `layers.findings` skips every file in no layer, `layers.write_record` writes the
playbook's layers rather than the tree's, and `front_door.record_problems` never reads a `TODO(architect)` marker. No
kit step carried an adopted tree's layers into a playbook, so the person had to hand-write `[architecture]` and a
`[testing] map` that fit each other (run record 7100000199, AD-05; reproduced in this build).

## Decision

1. `gates/layers.py --draft [--root DIR]` reads the product's source files (`.py`; with an Accepted Node stack record
   the Node pack's suffixes), leaving out hidden folders, `SKIP_DIRS`, the `test_dirs`, the kit's `lint_paths`, `docs/`
   and `config/`. It descends from the root while a level holds one folder and no loose file, and at the first level
   with two or more groups proposes each subfolder as a layer (`<folder>/**`, named by its slug) and the level's loose
   files as one layer named after their folder (the project folder's name at the root), with `-2`, `-3` for a repeat.
   It proposes as `allow` each direction a Python import takes today, none for Node (`no reader for node`), and a
   `[testing] map` of one code per layer path with the first `test_dirs` entry plus `/**`. It writes nothing; fewer than
   two groups or `mode = "init"` proposes nothing.
2. With `mode = "adopt"`, two or more composed layers and no source file in any of them, the `layers` step fails once,
   `SPEC-0072 rule 5: no source file is in any layer (key: architecture.layers)`, in `layers.py` and `run_gates.py`.
   The runner holds it by no baseline and writes none from it (`layers.unheld`). Another mode gives
   `not run: no source file in any layer yet`. `--write-record` in adopt mode refuses the same set and writes nothing.
   A runner failure whose class starts `key: ` prints it as `(key: ...)`.
3. `front_door.record_problems` fails each of Context, Parts, Data stores, Outside services, Needs and Diagram that holds
   `TODO(architect)`, one line per section that never quotes the line, so the `architecture-record` step and
   `check-design` both fail it. A held record (`record_held`) stays `not run`, and the template keeps its markers.
4. In adopt mode, when the composed layers hold no source file, `steward_owner.py standard` shows the draft beside the
   playbook's layers (team: each layer, its paths and each direction; solo: one plain line). After the person's recorded
   `Setup: standard: confirmed` (team mode: a spec approver), `steward_owner.py draft --slug SLUG --layers FILE` writes
   the project's Proposed ADR first, listing the layers and directions, then `front_door.py derive-write --layers FILE`
   writes the two tables in place of `map = []`, each `allow` entry naming that ADR and `modules` naming the declared
   shipped work type. If `check_playbooks.findings` refuses the playbook, neither file is kept. Without the recorded yes
   it refuses and writes nothing. `[delivery] work_type` stays the owner's line.
5. `skills/adopt/SKILL.md` ends with running `layers.py --draft`, showing its output unchanged and taking it to the
   standard confirmation.

## Consequences

An adopted product's checks no longer pass while reading nothing of its code, and an unfilled record is red. A
project already on main whose record still holds a marker goes red on upgrade until the record is filled (`Q-HE-3`,
read conservatively). The drafted layers live in the project's derived playbook (`Q-HE-1`). On main the declaration
(SPEC-0038 rule 5, `playbook_format._declared`) accepts only a shipped work type, so the gates read that playbook only
once a declaration may name a derived one. This build does not change that (`Q-1842-1`).

## Residual

- 2026-11-23: declaring a derived playbook in `[delivery] work_type` is outside this build (`Q-1842-1`). Until it is
  allowed, the drafted layers are written and checked but not yet the ones the `layers` step reads.

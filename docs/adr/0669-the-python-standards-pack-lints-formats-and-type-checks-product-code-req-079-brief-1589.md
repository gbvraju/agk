# ADR-0669: The Python standards pack lints, formats and type-checks product code (REQ-079)

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: SPEC-0072, SPEC-0002, ADR-0007, ADR-0665, ADR-0666, ADR-0672, brief #1589, plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `config/` (`config/playbooks/default.toml`), `scripts/agk/` (the new
`gates/python_pack.py`, `run_gates.py` and `config.py`), `tests/kit/` (the new `test_python_pack.py`), `kit/`
(`kit/manifest.json`, `kit/templates/agk.toml`, `kit/templates/agk.adopt.toml`) and `agk.toml` (the `[[testing.map]]`
entries). `kit/hashes.json` is not edited by hand.

## Context

SPEC-0072 (Approved, REQ-079) rule 12 build (e) builds rule 6 and rule 8's bring-your-own `floor`, Python first. On the
default branch at f5c1c29 (2026-11-21) no playbook holds a `[[standards]]` entry (ADR-0665 left them to this build),
`run_gates.py` runs only `[[gates]]` (ADR-0666), and a project's own code is not linted, formatted or type-checked:
`agk-lint` reads `lint_paths`, the kit's folders, with `AGK_RUFF_FLAGS`. `config/ci-tools.txt` pins `ruff==0.17.4` and
`mypy==2.3.1`. Rule 12 asks for this build's own ADR for the new `agk.toml` setting.

## Decision

1. A new top-level setting `project_lint_paths` in `agk.toml`, a protected file: a non-empty list of relative globs, the
   product code the pack reads. Unset, the pack reads the paths of the composed `[architecture] layers`. Any other form
   (a string, an empty list, an absolute path, a `..` part, a drive) is refused naming `setting: project_lint_paths`,
   never the value. The templates carry it as a comment only, so no project's settings change. `lint_paths`,
   `AGK_RUFF_FLAGS` and `agk-lint` are unchanged (SPEC-0002 rule 10, ADR-0007 decision 8).
2. `config/playbooks/default.toml` holds the two Python entries, `python-pyproject` and `python-pip`, so every playbook
   composes them (the brief's "one entry each" is met by composition, not by seven copies): steps `python-lint`,
   `python-format` and `python-type`; `config = "pyproject.toml"`, the file the foundation writes from
   `kit/templates/stacks/python-pyproject/`; `rules = { tool = "ruff", version = "0.17.4", codes = ["E", "F", "I", "B",
   "UP"] }`, the kit's own `AGK_RUFF_FLAGS` codes and the template's `[tool.ruff.lint] select` (the brief's Q-1). The
   `rules` table names one tool (ADR-0665's form), so mypy's pin, 2.3.1 from `config/ci-tools.txt`, is held by the pack
   module and a test keeps both equal to that file.
3. `run_gates.py` runs, after the gates, each pack module of its `PACKS` once for the composed entries it serves, only
   when the module is on. `scripts/agk/gates/python_pack.py` is on only when the one Accepted stack record chose a Python
   runtime (`pins.chosen`, ADR-0672); the kit's own repository and a project with no stack chosen run no pack. A step
   name the module does not hold is refused naming the stack.
4. The pack's steps, over the product `.py` files of decision 1 (less hidden and environment folders and the kit's own
   `lint_paths`): `floor`, then `ruff check --select <codes>`, `ruff format --check` and `mypy --strict-optional
   --disallow-untyped-defs --disallow-incomplete-defs` (the brief's Q-2: typed from the start, not `--strict`; a team
   tightens in its own `[tool.mypy]`). Each tool runs as `<this python> -m <tool>` with an argument list, never a shell,
   and writes no cache. A finding prints `FAIL gates: standards <stack> <step>: SPEC-0072 rule 6: <lint rule CODE | type
   rule code | the file is not formatted> (path class: <glob>)`, never a file name or a value. A tool missing from this
   Python, or one that exits abnormally, is a failure naming the tool or step and the setting, never a silent pass.
5. The `floor` (rule 8, Q-S0072-14): the pack's `config` file must enable every code of `rules` (`select`, else ruff's
   own default, plus `extend-select`; `ALL` enables all) and ignore none of them, even in part (`ignore`,
   `extend-ignore`, `per-file-ignores`); each missing code is one line naming it and `setting: standards.config`. A
   configuration may add codes. A missing or unreadable file is one line naming the same setting.
6. New projects (`mode = "init"`) have the pack on from the stack record's acceptance. An adopted project's baseline is
   build (g)'s (brief #1600); this build reformats nothing.

## Consequences

A Python product's own code is red on an unused import, a type fault or an unformatted file once its stack is chosen,
inside the existing `governance` job, `make governance` and `prepush.py`, with no workflow, ruleset, required-check or
`agk.mk` change. A team's own ruff configuration that drops a pinned rule is refused naming the rule. The kit's own lint
is unchanged. A machine without ruff or mypy in the governance Python fails naming the tool.

## Residual

- 2026-11-21: until build (g) lands, an adopted project whose stack record is Accepted gets the pack with no baseline;
  brief #1600 adds it (due 2027-03-31).
- 2026-11-21: the packs of the other stacks of SPEC-0072's Residual, one per build (due 2027-03-31).

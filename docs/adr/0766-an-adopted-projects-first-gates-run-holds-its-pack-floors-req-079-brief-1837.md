# ADR-0766: An adopted project's first gates run holds its pack floors and never passes a pack that read nothing (REQ-079)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: SPEC-0072 rules 6, 7 and 8, ADR-0668, ADR-0669, ADR-0680, ADR-0702, ADR-0739, ADR-0740, ADR-0743, brief #1837, plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (`run_gates.py`, `gates/node_pack.py`,
`gates/python_pack.py`, `doctor.py`) and `tests/kit/` (`test_adopt_first_run.py`, `test_gate_baseline.py`,
`test_node_pack.py`, `test_python_pack.py`, `test_personal_gate.py`). `kit/hashes.json` is not edited by hand.

## Context

On main at e1fdb41 (2026-11-23) an adopted project (`mode = "adopt"`) goes red on its first gates run, which SPEC-0072's
negative cases forbid: the rule 8 floor steps (`floor` of both packs, the Node `type-floor`) are not tallied, so
`run_gates.pack_results` never holds them to a baseline and the project's own lint or compiler configuration fails
the run. Rule 7 forbids rewriting that configuration. Two holes sit beside it: `ratchet` passes a step whose tool did
not run (it counts no file, so no count rises), which hides every lint fault of an adopted Node product behind an
empty baseline; and a pack whose `project_lint_paths` (or layers) match no product file prints `ok standards <stack>`
although it checked nothing, against ADR-0668's rule that a step that cannot read the project is `not run`.

## Decision

1. The floors are tallied like the other pack steps: `floor` counts its lines against the `[[standards]] config`
   path, `type-floor` against each compiler configuration it read (`tsconfig.json` and each referenced one); a
   missing or unreadable configuration counts 1. `ratchet` therefore writes
   `config/agk-baseline/standards-<stack>-floor.txt` (and `...-type-floor.txt`) on the adopted first run, or on
   `--baseline` in any mode, and prints `standards <stack> floor (baseline): <n> held (setting: standards.config)`
   (`type-floor`: `(path class: tsconfig.json)`), never `ok`; a rising count fails with the rule 7 line. With no floor
   file outside adopt mode (`init`, or no `mode`) the floor fails as before. The kit never edits the product's
   configuration (`Q-1837-1`, the brief's `Q-HD-1`: the conservative reading; the reviewers may amend rule 7 to name
   rule 8).
2. A failure line of a tallied step that counts no file (`the <step> tool did not run`) is never held: `ratchet`
   returns the step's failures and writes no baseline, in every mode, with or without a file. The one exception is the
   Node `node-lint` step while the Node floor is held for an unreadable configuration: it prints `not run standards
   node lint: the pack's configuration is held (setting: standards.config)` and is named in the last line
   (`Q-1837-3`, the brief's `Q-HD-3`).
3. A pack with no product file in scope runs no step (the Python floor included, `Q-1837-2`) and prints
   `not run standards <stack>: no product file in scope (setting: project_lint_paths)`, or `(key: architecture.layers)`
   when `project_lint_paths` is unset, named in the last line; the exit code is unchanged.
4. A pack that held or did not run a step prints no `ok standards <stack>` row.
5. `doctor.py` prints one `warn standards:` line per floor baseline file that holds a line, and one per pack that is on
   and reads no file; never a file name, a rule code or a value, and no exit code changes.

## Consequences

An adopted project's first `make governance`, `governance` job, `kit_root.py governance` and `prepush.py` are green with
its own configuration held and named, and a held floor can only fall. A broken lint, format or type tool fails every
run. The personal sidecar's floor (`personal.gates_step`) fails on failure rows only, so a held floor passes it. The
kit's own repository runs no pack, and its output is unchanged. A team that commits a new floor file after adoption
needs an ADR that names it, as for any new baseline file (`check_protected_changes.py`).

## Residual

- 2026-11-23: the AD-09 brief (ADR-0773) may change `ratchet` again; it builds on this one (`Q-HD-4`).

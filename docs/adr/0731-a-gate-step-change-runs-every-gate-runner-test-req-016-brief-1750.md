# ADR-0731: A change to a gate step runs every test that runs the gate steps together (REQ-016)

- Status: Accepted
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1750, issue #1747, brief #1748, brief #1651
- Requirements: REQ-016

Protected classes: `agk.toml`, `tests/kit_dev/`

## Context

`scripts/agk/run_gates.py` loads each gate step by name (`importlib.import_module(f"gates.{name}")`), so no test file
imports a module of `scripts/agk/gates/` and the importer rule of the test selection finds nothing for one. On
2026-11-22 a change to `scripts/agk/gates/environment_settings.py` (#1746) selected 6 test files, without
`tests/kit/test_tests_floor.py`, which runs the runner; after the merge that test failed on the default branch (#1747).

## Decision

1. The `scripts/agk/gates/*.py` entry of `[[testing.map]]` in the kit's own `agk.toml` names every test file of
   `tests/kit/` and `tests/kit_dev/` that runs the gate runner, so a change to any gate step selects them all. Each gate's
   own entry is unchanged; no code of the selection changes.
2. A test file runs the gate runner when it has an `import run_gates` or `from run_gates` line, or names `run_gates.py`
   in a string that is not a docstring (a command that starts it; the conservative reading of Q-30A-1).
3. `tests/kit_dev/test_gate_runner_map.py` keeps the entry true: it fails when such a test file is missing from the entry
   and when the entry names a file that does not exist, naming the path class and the setting `testing.map`, never a
   file. It lives in `tests/kit_dev/` because `tests/kit/` runs in every project, whose `agk.toml` has no kit map.

## Consequences

A gate change selects about 13 more test files (about 21 seconds on one process), in governance and in `prepush.py` alike.
A project using AGK sees no change: the map is the kit's own, and the new test is not shipped.

## Residual

- Q-30A-1 (2026-11-22): counting a subprocess command naming `run_gates.py` is the conservative reading; none does today.

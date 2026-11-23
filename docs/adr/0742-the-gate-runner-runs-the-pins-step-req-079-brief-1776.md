# ADR-0742: The gate runner runs the pins step once a stack is chosen (REQ-079)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: SPEC-0072 rules 3, 4 and 7, ADR-0672, ADR-0676, ADR-0680, ADR-0731, brief #1776, plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (`run_gates.py`, `gates/pins.py`), `agk.toml` (the
`scripts/agk/gates/*.py` entry of `[[testing.map]]`) and `tests/kit/` (`test_pins.py`, and the samples of
`test_run_gates.py`, `test_layers_step.py`, `test_node_pack.py`, `test_python_pack.py` and `test_skeleton_basics.py`).
`kit/hashes.json` is not edited by hand.

## Context

On main at ee47218 (2026-11-23) `scripts/agk/gates/pins.py` holds the runner's interface, but no playbook gate names
`step = "pins"` and `run_gates.py` runs only `bom` and `licences` as product steps, each only where a lock is read. So
an adopted product with version ranges and no lock fails `gates/pins.py` run alone while governance exits 0 with no
pins row. SPEC-0072's proof asks that such a sample be red.

## Decision

1. `run_gates.py` runs `pins` as the first of its product steps (`pins`, `bom`, `licences`), where `pins.applies` is
   true: a `[delivery] work_type` is declared. Each failure is one row naming the rule and the component class, with the
   build file or lock as its path class, never a name or a version.
2. With a work type and no stack chosen (no Accepted stack record, or none whose runtime the step knows), `pins.skipped`
   gives `not run: no stack chosen`, printed as one not-run row and named in the runner's last line, never `ok`.
3. `pins.counts` gives the findings per build file or lock, one per dependency or part, so the runner's baseline
   (rule 7) holds it: in `mode = "adopt"` the first run writes `config/agk-baseline/pins.txt`, and a new range or a lost
   lock entry then fails as `SPEC-0072 rule 7`.
4. A sample of another step that chose a stack now carries the stack's lock with no dependency, so `pins` passes
   there, and keeps `bom` off as before (it had no lock, so `bom` never ran; `bom` has its own tests). A sample that
   chose Node with no `package.json` (the no-pack tests of brief #1685 and the layers step) now fails `pins` alone,
   since a chosen stack's missing build file is red; those tests assert that `pins` is the only failure.
5. `tests/kit/test_pins.py` now imports the runner, so it joins the `scripts/agk/gates/*.py` entry of
   `[[testing.map]]` (ADR-0731).

## Consequences

A project with a chosen stack whose dependencies are not pinned exactly and locked fails `governance`, `make
governance` and `prepush.py`, with no workflow or ruleset change; the personal sidecar runs the same runner. A project
with no work type, the kit's own repository among them, prints the same lines as before.

## Residual

- 2026-11-23: with the Node pack on (it needs a `package.json`), the `not run standards: no pack for node` line of
  brief #1685 now prints only on a run that `pins` fails; the line is unchanged.

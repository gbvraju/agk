# ADR-0702: A stack with no standards pack is told so

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1685, SPEC-0072 rule 6, ADR-0669, ADR-0668
- Requirements: REQ-079

## Context

The standards packs of SPEC-0072 rule 6 serve Python only (`PACKS = ("python_pack",)` in `scripts/agk/run_gates.py`).
A project whose Accepted stack record chose Node ran the gates and saw `ok gates (6 check gates; not run: tests-first,
contract-tests, mock-parity, layers)`: no line said the pack did not run, so the code could be read as checked.
SPEC-0072's residual of 2026-11-18 puts the packs after Python one per build, due 2027-03-31.

## Decision

When the one Accepted stack record chose a runtime that no module of `PACKS` serves, `run_gates.py` prints
`not run standards: no pack for <stack>`, the stack class of `config/stack-signals.toml` (`unknown` outside it), never
a version, and names `standards` in the `not run:` list of its last line. The exit code is unchanged: a not-run is
neither a failure nor a pass. `doctor.py` prints one line `warn standards: no pack for this stack yet (setting: stack
record)` by the same reading, with no change to its exit code. With no work type, no Accepted record or a Python
stack, nothing changes. No pack is built here.

Protected path classes changed: `scripts/agk/` (`run_gates.py`, `doctor.py`) and `tests/kit/` (`test_run_gates.py`,
`test_delivery_declaration.py`, `test_layers_step.py`).

## Consequences

Every product of a stack without a pack sees the gap in governance, prepush and the sidecar run, which all run the
gate runner. The line is the same at every governance level, layout, execution and review mode.

## Residual

- A record naming two runtimes is no chosen stack today (`pins.pick`), so it prints nothing new; the brief's answer 4
  for it waits on a ruling (Q-1685-1), 2026-12-31.
- The Node pack itself (brief Q-1): the owner's scope choice, against the residual's date 2027-03-31.

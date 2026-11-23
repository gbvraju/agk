# ADR-0743: An adopted project's committed secret is held, named and counted, never shown as ok (REQ-079)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: SPEC-0072 rules 2 and 7, ADR-0673, ADR-0676, ADR-0680, ADR-0742, brief #1777, plan #661
- Requirements: REQ-079

Protected classes this pull request changes: `scripts/agk/` (`run_gates.py`, `doctor.py`, `gates/committed_secrets.py`,
`gates/licences.py`, `gates/baseline.py`) and `tests/kit/` (`test_gate_secrets_settings.py`, `test_product_deps.py`,
`test_gate_baseline.py`). `kit/hashes.json` is not edited by hand.

## Context

On main at 9bbfd77 (2026-11-23) the `committed-secrets` step and the `licences` step return no finding at all in
`mode = "adopt"`, "held until brief #1600's baseline". That baseline (ADR-0680) has landed, but neither step was moved
onto it, so an adopted project with a tracked key shape prints `ok secrets`, with no held row and no baseline file. A
committed secret is a leak whether or not the project is adopted.

## Decision

1. Both steps drop their `mode = "adopt"` early return and gain `counts(root, playbook)`: the findings per file (a
   tracked file's secret shapes, a secret file or an unignored environment file as one each, an example settings
   file's values; the lock's failing packages, or the licence setting when it is not of its form). The runner's
   ratchet (ADR-0680) then writes the baseline on an adopted project's first run, and a new finding or a higher count
   fails as `SPEC-0072 rule 7`. With `mode` unset or `init` nothing is written and the step fails as before.
2. A step module with `HELD = True` (these two) that passes on a baseline holding findings prints one row
   `<gate id> (baseline): <n> held (path class: <class>)`, `n` the count of today's findings, never `ok <gate id>`. It
   counts as a check gate and changes no exit code. The other steps with counts (`layers`, `pins`, the packs) keep
   their `ok <id> (baseline)` row.
3. The `secrets` gate's baseline file is `config/agk-baseline/committed-secrets.txt`, its step's name, not
   `secrets.txt`: `secrets.*` is a secret file name of the data guard (`guard.secret_file_name`), which the step itself
   fails once the file is committed. `baseline.name` maps that one gate id; the file holds paths and counts only.
4. `doctor.py` prints one `warn secrets:` line while that file holds a line, naming `docs/runbooks/leaked-secret.md`
   and the path class `config/agk-baseline/`, never a file or a value; it changes no exit code. Lowering after the
   secret is removed and rotated is the existing `run_gates.py --baseline`.

## Consequences

An adopted project sees each existing committed secret and disallowed licence on every gate run and in the doctor,
and a new one fails `governance`, `make governance`, `prepush.py` and the personal sidecar's floor, with no workflow
change. A project that is not adopted, the kit's own repository among them, prints the same lines as before. The
standalone `gates/licences.py` run, which has no baseline, now reports an adopted project's findings.

## Residual

- 2026-11-23: an adopted project whose first run is clean gets an empty `committed-secrets.txt`, as every step with
  counts does (ADR-0680); that empty file is what makes a later secret fail rather than be held.

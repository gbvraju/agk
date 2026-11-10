# ADR-0406: The personal floor, a secret scan and no new failing test at every level

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0267, ADR-0400, SPEC-0041, brief #947
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

SPEC-0041 rule 18 fixes a floor of two steps that runs at every level of rule 17 and that no setting lowers: a secret
scan of the branch's commits and no test that passed on the base failing on the head. Build (h), first part (ADR-0400),
recorded the baseline and checked the ten `[personal]` keys but ran no floor. ADR-0267 asks each build of the spec for
its own ADR naming its classes; this is build (h), second part.

## Decision

1. `scripts/agk/personal.py` gains `floor [--clone DIR] [--sidecar DIR] [--base REF] [--approve]`. It judges the head
   against the merge base with `REF`, else with `origin/HEAD`; no merge base is refused naming `--base`.
2. Step one is `prepush.secret_scan` unchanged (gitleaks with `--redact` over merge base to head). Where gitleaks is
   not on the path the step fails with `floor: secret scan not run (gitleaks not installed)` (`Q-S0041-15`); the
   deferral to CI of ADR-0327 is never read here. A finding fails the step naming it and the runbook, never the
   finding's text. The scan runs without `--approve`: it runs no product code.
3. Step two runs only with `--approve`: the test command runs once on the base tree and once on the head tree, each
   written with `git archive` into the sidecar's `cache/trees/<sha>/`. With `{junit}` a test id that passed on the base
   and fails on the head fails the step and is named; a test new on the head or already failing on the base does not.
   Without `{junit}` a passing base and a failing head fail, and a failing base is `unknown`, which never passes
   (`Q-S0041-19`). Without `--approve` it prints the run it would make, runs nothing and the floor does not pass.
4. `level` is read only to print it; no key or value changes either step (principle 11). It prints one line per step
   and one result line, exits 0 only when both steps pass, and writes nothing in the clone or under its `.git/`.
   `prepush.py` is imported, not changed; `records/gates/<head>.json` stays rule 19's.

## Consequences

A developer can run the floor on a branch before pushing and see, by test id, what the change broke. The kit's
scanner step is shared with team mode, so a later change to it applies to both.

## Residual

- 2026-11-10: importing `prepush` pulls in `socket` for its lock's host name; the floor opens no connection, but
  rule 28's import test, where one is written for `personal.py`, would need to allow it (`Q-947-2`).
- 2026-11-10: the two runs have no time limit, as the baseline's run has none (ADR-0400).
- 2026-11-10: the floor does not read `records/baseline.json`; it reruns the base, so a flaky test can fail it.

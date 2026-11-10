# ADR-0401: The smoke run by change kind, and its test map entry

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0270, SPEC-0044, brief #923
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

SPEC-0044 rule 8 asks for `scripts/agk/smoke.py`, new and installed, which chooses the after-merge smoke run from the
changed paths and runs it under the heavy-step lock with `--run`. ADR-0270 names `scripts/agk/`, `tests/kit/` and `kit/`
for the builds of SPEC-0044, but its decision 5 says no build changes `agk.toml`. This build adds one `[[testing.map]]`
entry to `agk.toml` for the new script, as every new script has, so ADR-0270 cannot cover it alone (session rule 36), and
the brief's Correction of 2026-11-10 asks for this ADR.

## Decision

1. `scripts/agk/smoke.py` and the `[testing] smoke` shape check in `scripts/agk/impact.py` are built as SPEC-0044 rule 8
   and ADR-0270 say; its tests are `tests/kit/test_smoke.py`, and `kit/manifest.json` lists the script.
2. `agk.toml` gains one `[[testing.map]]` entry, `scripts/agk/smoke.py` to `tests/kit/test_smoke.py`, and nothing else.
   The entry is test bookkeeping: it selects the script's tests and decides no setting of the project.
3. No decision of SPEC-0044 or ADR-0270 changes; this ADR only names the classes of this build, and the `agk.toml`
   exception of decision 2 applies to this entry alone.

## Consequences

A change of `smoke.py` selects its tests in prepush and CI. A later build of SPEC-0044 that touches `agk.toml` still needs
its own ADR naming it, as ADR-0270 decision 5 stands for every other change of that file.

## Residual

None (2026-11-10).

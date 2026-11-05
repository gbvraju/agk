# ADR-0282: This repository's proof_timeout is 1800 s (REQ-051, brief 568)

- Status: Proposed
- Date: 2026-11-05
- Deciders: maintainers
- Related: ADR-0258, SPEC-0044
- Requirements: REQ-051

Protected classes: `agk.toml`, `tests/kit_dev/`

## Context

On 2026-11-05 four builders (#563, #564, #565, #567) had prepush end their test step at the default
`proof_timeout` of 900 s with "the tests did not fail, they did not finish". The measured full-suite
times on the builders' 2-CPU machines were 859 s, 915 s, 1161 s and 1161 s: three of the four runs
exceed 900 s, and the fourth is within 41 s of it. SPEC-0044 rule 9 (Approved)
gives the headroom formula of ADR-0258, ceil(n × 1.5 / 60) × 60, which for 1161 s is 1800 s, and
keeps changing the setting a person's change with an ADR. This ADR number was reserved for brief
#568 by the conductor.

## Decision

1. `agk.toml` sets `proof_timeout = 1800` as a top-level key beside the test settings, before the
   `[flow]` table. Nothing else in the file changes apart from the comment above the line.
2. No default in code and no kit template changes: `common.DEFAULT_CONFIG` and
   `kit/templates/agk.toml` keep 900, and adopters keep it until `doctor.py` suggests otherwise
   (SPEC-0044 rule 9).
3. One kit-only test (`tests/kit_dev/test_repo_proof_timeout.py`) fails when this repository's
   value falls below the headroom of 1161 s, so a later lowering is caught.

## Consequences

- A passing full suite of up to 1800 s is no longer cut off in prepush or proof; a run that hangs
  now takes up to 1800 s instead of 900 s before it ends.
- The suite itself is not shortened; the later builds of REQ-051 (parallel workers) do that, and the
  value can be lowered again, with an ADR, once a new measurement allows it.

## Residual

- 2026-11-05: re-measure the full suite after REQ-051 build (b) merges and revisit the value
  (due 2026-12-31).

# ADR-0060: criterion g starts now, read-only; the facts are published

- Status: Proposed
- Date: 2026-10-21
- Deciders: maintainers
- Amends: ADR-0025
- Related: ADR-0021, ADR-0025, ADR-0053
- Requirements: REQ-020

## Context

K5 early is complete: ADR-0053 opened three items before the friends launch and all three are built, released (kit 0.29.0 to 0.31.0) and read on a real report (`docs/runs/k5-early-live-1.md`). ADR-0025
decision 6 makes the portal's first governed merged pull request the proof of exit criterion g, and its plan table (decision 3) starts that run "from 2026-11-09". The maintainers need a
business-readable view of the weekly numbers now. The read-only slice of the portal depends on neither the first outside developer's run nor the pilot's scored weeks (2026-10-26 and 2026-11-02): it reads the
facts document and writes nothing.

## Decision

1. **Criterion g starts now.** The criterion g run of ADR-0025 decision 6 starts when this ADR is merged, instead of from 2026-11-09. The row of ADR-0025's plan table (decision 3) reads, as amended here:
   `Criterion g run (decision 6) | from the merge of ADR-0060 (in progress, ADR-0060)`. No other row of that table moves, is dropped or is shortened, and no check, fix list or clearance is skipped for speed
   (ADR-0025 decision 3).
2. **The scope stays read-only.** Beyond its first merged pull request the portal builds only its read-only slice until criterion a is met (ADR-0025 decision 6, unchanged). The action buttons and the
   single sign-on stay where ADR-0025 decision 5 puts them.
3. **The portal's repository is not named** in this repository (ADR-0025 decision 6, unchanged); this repository records the outcome only.
4. **One more item before the launch.** ADR-0053 decision 1 allowed exactly three items before the friends launch. It allows a fourth: the weekly product report also publishes the facts document it was
   rendered from, as a downloadable file of the workflow run, so that a reader outside the repository can use the same numbers (intake and build as pull requests A2 and A3 of the maintainers' brief). Nothing
   else is added; every other candidate in the residual register still waits for the K5-opening ADR proper.
5. **The register moves.** The portal's line in `docs/runs/residuals.md` (the K5 headline candidate) changes its status from `open` to `in progress, ADR-0060`; its text and due date do not change.

## Consequences

- The read-only slice can be built in parallel with the pilot's scored weeks, and the facts it reads exist as a file of each weekly run.
- Criterion a (the product owner answers the five questions from the report alone for two consecutive weeks) and the first outside developer's run are not affected and still gate the launch claim.
- The facts document becomes a published artifact of a workflow run: that is a new place where the numbers of a repository are readable, for those who can read the run (to be settled by the spec of the intake,
  not here).

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-215 | The brief says `Amends: ADR-0025, ADR-0053`, and to update ADR-0025's plan table row; `check_adrs` accepts one ADR in `Amends`, and an Accepted ADR changes only its Status line | `Amends: ADR-0025` (the plan and decision 6) and `Related: ADR-0053`, the amendment of ADR-0053 decision 1 stated in decision 4 above; the amended plan row is in decision 1 above, ADR-0025 itself unchanged. The check is not weakened. Proposed for ruling. |

## Residual

- 2026-10-21: the criterion g record lives in the portal's repository; this repository records its outcome (the first governed merged pull request) when the maintainers give it (due 2026-12-31).

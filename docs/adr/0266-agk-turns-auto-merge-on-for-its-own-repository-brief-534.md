# ADR-0266: AGK turns auto-merge on for its own repository (REQ-046, brief 534)

- Status: Proposed
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0261, ADR-0263, ADR-0265, SPEC-0039
- Requirements: REQ-046

Protected classes: `agk.toml`

## Context

SPEC-0039 rule 1 keeps `[flow] auto_merge` off by default, and the comment in `agk.toml` says that
turning it on in this repository is the owner's change, by an ADR in the same pull request. On
2026-11-04 the owner asked the conductor to use AGK's own auto-merge here, so that cleared pull
requests stop waiting on a hand merge. This ADR number was reserved for brief #534 by the conductor.

## Decision

1. `agk.toml` sets `auto_merge = true` and `auto_merge_method = "squash"` under `[flow]`. Nothing
   else in the file changes apart from the comment above the two lines.
2. Only the conductor merges, only through `merge_cleared.py --pr <n> --sha <sha>`, in the same act
   as posting `Verdict: cleared <sha>` (principle 2 and session rule 2 as amended by #531). Builders
   never merge.
3. Everything on the hold list of SPEC-0039 rule 5 stays with the owner, unchanged: releases, spec
   approvals, the protected classes `constitution/`, `config/reviewers.yaml`, the ruleset files and
   `.github/workflows/`, the hold label, drafts, `Depends-on` and conflicts, and anything while the
   red-branch issue is open or `paused = true`.
4. This pull request merges after #531 (build b, the guarded merge). Until then the setting only
   changes what `doctor.py` reports, because build (a) merges nothing.

## Consequences

- Ordinary cleared pull requests merge minutes after the verdict instead of waiting for the owner.
- The after-merge governance run and the red-branch stop arrive with build (c); until then the
  conductor checks the default branch after each merge by hand, as it does today.
- Turning it off is one pull request setting `auto_merge = false`, with an ADR.

## Residual

- 2026-11-04: until build (c) of SPEC-0039 is merged, nothing runs governance on the default branch
  after a merge made by `merge_cleared.py`; the conductor checks it by hand after each merge
  (due 2026-12-31).

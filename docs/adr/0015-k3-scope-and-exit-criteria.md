# ADR-0015: K3 scope and exit criteria

- Status: Accepted
- Date: 2026-10-15
- Deciders: maintainers
- Related: ADR-0001, ADR-0002, ADR-0007, ADR-0011, ADR-0012, ADR-0014
- Amends: ADR-0002
- Requirements: REQ-012

## Context

K2 is closed (PR #30). ADR-0002 defines K3 as "plugin and metrics": Claude Code plugin packaging (`/agk:init`,
`/agk:brief`, `/agk:review`, `/agk:doctor`), per-PR metrics recorded in the PR body and aggregated weekly, and optional
adopted components behind profile flags. Its residual says the exit criteria for K3 and K4 "need measurable thresholds
before those milestones start". ADR-0002 is Accepted and immutable, so this ADR amends it, for K3 only.

Residuals that fall due at K3 start (`docs/runs/residuals.md` and the ADRs): the upgrade path between kit versions
(ADR-0007, ADR-0008, SPEC-0002), `agk doctor` (ADR-0001, ADR-0003, SPEC-0001), the GitHub Action form of the reviewer
(SPEC-0003 rule 14), and reviewer effectiveness (shadow reviews 2 and 3: 0 of 3 human findings caught; the reviewer is
advisory and human review stays required).

## Decision

1. **K3 is delivered as four specs, each Approved before its code.**
   - **SPEC-0005 distribution:** the plugin, and how CI gets the checks.
   - **SPEC-0006 `agk doctor`.**
   - **SPEC-0007 metrics** (REQ-012).
   - **SPEC-0008 upgrade:** kit version to kit version, for init and adopt.
   Each spec is written Draft, reviewed, and set Approved by the maintainers; implementation of a spec starts only
   after it is Approved. A requirement for the plugin (REQ-014, "install and run agk as a Claude Code plugin") is added
   by an ADR when SPEC-0005 is drafted.
2. **Exit criteria for K3, measurable.** K3 is closed when all five hold:
   a. from a fresh repository, installing the plugin from the agk marketplace and running `/agk:init` gives
      `governance` green on GitHub with no file copied by hand;
   b. `/agk:doctor` reports every misconfiguration in its fixture set (ruleset missing or weaker than ADR-0001
      decision 3, required check missing, placeholder team, missing `origin/HEAD`, drift-audit schedule disabled) and
      reports none on a correctly configured repository; proven live on the sandbox;
   c. the 0.1.0 sandbox upgrades to the current kit with zero product files changed and governance green;
   d. per-PR metrics are recorded for every PR merged in agk for two consecutive weeks and aggregated weekly by the
      mechanism SPEC-0007 defines;
   e. the reviewer agent catches at least 3 of 5 recorded findings on a fresh run (the 3 from shadow reviews 2 and 3,
      plus at least 2 new human findings recorded during K3 that the reviewer was not tuned on, with at least 1 of
      those caught); otherwise it is removed from the default profile and documented as experimental. Either outcome
      closes the criterion.
3. **Dates.** The K3 target is 2026-11-30 and the K4 target is 2026-12-31. Residuals that fall due at K3 start are
   due 2026-11-30 in `docs/runs/residuals.md`.
4. **K4 exit criteria are deferred** to a K4-opening ADR, written before K4 starts and due 2026-12-01 (residual below).
5. **Unchanged.** ADR-0002's other lines (K0 to K2, the non-goals of v0, repository public from K0) stand. The K2
   rulings stand: the reviewer is advisory, human review stays required, and a recurring finding becomes a
   deterministic check, not a reviewer prompt.

## Consequences

- K3 has a finish line that a person can check without judgement, except criterion e, where either outcome counts.
- Four specs mean four reviews before any K3 code; the order of the specs is not fixed here.
- Criteria a to c need things this repository cannot show by itself (a marketplace install, a live sandbox); the
  proofs are recorded in `docs/runs/`, as for K1 and K2.
- Criterion d leaves the aggregation mechanism to SPEC-0007. The drift audit issue is not assumed to be it: a clean
  run writes nothing (SPEC-0004 rule 14).
- Criterion e needs at least 2 new human findings recorded during K3; they are recorded in the repository (K2
  ruling: human verdicts are recorded in-repo) before the reviewer is run on them.

## Residual

- 2026-10-15: K4 exit criteria need measurable thresholds before K4 starts; a K4-opening ADR states them (due 2026-12-01).

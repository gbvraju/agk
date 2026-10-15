# ADR-0015: K3 scope and exit criteria

- Status: Proposed
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
   d. per-PR metrics are recorded for every PR merged in agk for two consecutive weeks and aggregated by the drift
      audit issue;
   e. the reviewer agent either catches at least 2 of the 3 recorded shadow findings on a fresh run, or is removed
      from the default profile and documented as experimental. Either outcome closes the criterion.
3. **K4 exit criteria are deferred** to a K4-opening ADR, written before K4 starts (residual below).
4. **Unchanged.** ADR-0002's other lines (K0 to K2, the non-goals of v0, repository public from K0) stand. The K2
   rulings stand: the reviewer is advisory, human review stays required, and a recurring finding becomes a
   deterministic check, not a reviewer prompt.

## Consequences

- K3 has a finish line that a person can check without judgement, except criterion e, where either outcome counts.
- Four specs mean four reviews before any K3 code; the order of the specs is not fixed here.
- Criteria a to c need things this repository cannot show by itself (a marketplace install, a live sandbox); the
  proofs are recorded in `docs/runs/`, as for K1 and K2.
- Criterion d depends on the weekly aggregation of SPEC-0007 and on the drift audit issue, which a clean run does
  not write (SPEC-0004 rule 14); SPEC-0007 has to say how a week with metrics but no findings is aggregated.

## Residual

- 2026-10-15: K4 exit criteria need measurable thresholds before K4 starts; a K4-opening ADR states them (due 2027-03-31).
- 2026-10-15: the dates of K3 and K4 are not fixed; due dates that say "K3 start" or "K4 start" use placeholders until
  they are (due 2027-01-31).

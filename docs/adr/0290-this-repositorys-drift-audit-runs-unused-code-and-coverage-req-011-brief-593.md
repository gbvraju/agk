# ADR-0290: This repository's weekly drift audit runs its unused-code and coverage commands (REQ-011, brief 593)

- Status: Proposed
- Date: 2026-11-05
- Deciders: maintainers
- Related: ADR-0177, ADR-0282, SPEC-0004
- Requirements: REQ-011

Protected classes: `agk.toml`, `tests/kit/`

## Context

`agk.toml` sets `unused_code = ""` and `coverage = ""`, so the Saturday drift audit (SPEC-0004
rule 25, D9) runs neither for AGK itself, although the kit already runs both commands for a project
that sets them and lists the output, never blocking. The owner decided, in chat on 2026-11-06
(quoted as data): "Yes please" to turning on the dead-code finder and coverage, a weekend cleanup
brief, cleaning tests without plain deletion, and fixing the audit's false findings first. This
ADR number was reserved for brief #593 by the conductor.

## Decision

1. `agk.toml` sets `unused_code` to vulture over `scripts/agk` and `.claude/hooks` at
   `--min-confidence 80`, installing vulture first when it is missing, the way `project_tests`
   installs pytest (the drift-audit job installs no toolchain).
2. `agk.toml` sets `coverage` to a command whose last line is the covered percentage of
   `scripts/agk`. The full kit suite takes 1161 s alone, so the command runs a named part of it
   (the check, route, drift, core, reviewers and session tests, 310 s measured) with coverage.
3. No whitelist file is added: at confidence 80 vulture reports no name the kit calls dynamically.
   A whitelist may be added later only for names called by name (a hook registration,
   `if __name__`, a `getattr`), each line with a reason; a test holds that rule and a second test
   forbids the other ways to hide a finding in the command.
4. `tests/kit/test_drift_own_config.py` is new, and `tests/kit/test_drift_unused_code.py` no longer
   expects this repository's `agk.toml` to be empty. No code under `scripts/`, no workflow and no
   template changes; the kit defaults and templates keep both settings empty.

## Consequences

- The next Saturday audit lists this repository's unused-code lines and its covered percentage,
  never blocking. The coverage figure is of the named part only and read as a trend, not a total.
- Vulture at 80 lists unused variables, imports and unreachable code; an unused function is rated
  60 and is not listed until the threshold is lowered (a later change with an ADR).

## Residual

- 2026-11-05: decide whether the coverage command should run the full suite once the parallel
  workers of REQ-051 shorten it

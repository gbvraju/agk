# ADR-0375: One check_runbooks step in the governance workflow

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: SPEC-0056, SPEC-0007, ADR-0372, brief #802, pull request #803, amendment 146
- Requirements: REQ-063

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `agk.mk`, `agk.toml`

## Context

SPEC-0056 rule 5 makes `check_runbooks.py` a step of `make governance`. SPEC-0007 rule 13 and REQ-012
AC1 need one step of `.github/workflows/governance.yml` for each command of `agk-governance`, and a
test holds the two equal. SPEC-0056 rule 14 and ADR-0372 decision 6 say that no build changes a
workflow. The three cannot all hold, so build (a) stopped with its test red and asked (`Q-802-1`).
The maintainer ruled option 1 on pull request #803 (comment 6724053592): one `check_runbooks` step
in `governance.yml`, with an ADR and an amendment of SPEC-0056 rule 14. A workflow change always
needs its own ADR (session rule 36), and `Covered-by:` cannot cover one (ADR-0271).

## Decision

1. `.github/workflows/governance.yml` gains one step, `check_runbooks`, directly after
   `check_playbooks`, running `python scripts/agk/check_runbooks.py`. It runs unless the run is
   cancelled, the description was only edited or the kit is paused: the same condition as
   `check_playbooks`, since it reads no pull request body.
2. The count of check steps goes from 14 to 15, in the tests that hold it. SPEC-0007 rule 13 is
   kept: one step per command.
3. This changes ADR-0372 decision 6 for this one step and for nothing else. Builds (b), (c) and (d)
   of SPEC-0056 change no workflow, and no ruleset or required check changes: the required check
   stays the job `governance`.
4. Build (a) of SPEC-0056 cites this ADR and not `Covered-by: ADR-0372`, and it names here every
   protected path class it changes.
5. Amendment 146 proposes the matching text of SPEC-0056 rule 14. It is not applied to the spec
   here (principle 6).

## Consequences

CI runs the runbook check on every commit of a pull request and on the default branch, in the kit
and, through the installed workflow, in a project. The check is cheap: it reads files, runs nothing
and needs no network. With no `docs/runbooks/` folder the step prints `skipped (no runbooks)`.

## Residual

- 2026-11-08: REQ-063 AC5 says that no workflow changes when the kit reports a red branch, blocked
  Actions or a finding. That reads on the reporting of builds (c) and (d), which is unchanged, and
  this ADR does not edit it; whether its text should name this step is `Q-802-4` (due 2027-03-31).

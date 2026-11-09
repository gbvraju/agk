# ADR-0381: One check_acceptance step in the governance workflow

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: SPEC-0051, SPEC-0007, SPEC-0026, ADR-0340, ADR-0375, brief #762, pull request #813, amendment 147
- Requirements: REQ-058

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `agk.mk`, `agk.toml`

## Context

SPEC-0051 rule 5 makes `check_acceptance.py` a step of `make governance`. SPEC-0007 rule 13 and REQ-012
AC1 need one step of `.github/workflows/governance.yml` for each command of `agk-governance`, and a
test holds the two equal. SPEC-0051 rule 11 and ADR-0340 decision 6 leave only build (c) a workflow
change, so build (b) stopped with its test red and asked (`Q-762-1`). The maintainer ruled option 1
on pull request #813: one `check_acceptance` step in `governance.yml`, with this ADR and amendment
147 of SPEC-0051 rule 11. A workflow change always needs its own ADR (session rule 36), and
`Covered-by:` cannot cover one (ADR-0271).

A second test stopped the same build (`Q-762-5`). `tests/kit_dev/test_start_discovery.py::test_ac6_no_other_script_reads_the_discovery_item`
lists the scripts that may hold the word `Discovery`, and SPEC-0051 rule 3 fixes the record's line as
`- Discovery: docs/discovery/<slug>.md`, so the check has to name it. The test guards SPEC-0026's
charter item, which this check never reads. The maintainer ruled that `check_acceptance.py` joins
the list, named here with `tests/kit_dev/`.

## Decision

1. `.github/workflows/governance.yml` gains one step, `check_acceptance`, directly after
   `check_runbooks`, running `python scripts/agk/check_acceptance.py`. It runs unless the run is
   cancelled, the description was only edited or the kit is paused: the same condition as
   `check_runbooks`, since it reads no pull request body.
2. The count of check steps goes from 15 to 16, in the tests that hold it. SPEC-0007 rule 13 is
   kept: one step per command.
3. `check_acceptance.py` joins the list in `test_ac6_no_other_script_reads_the_discovery_item`. It
   reads SPEC-0051's record line and never the charter item, so the test keeps guarding that item
   against every other script.
4. This changes ADR-0340 decision 6 for this one step and for nothing else. Build (c)'s CI line
   that passes saved comments still needs its brief's quoted owner's yes and its own ADR, and
   builds (d) and (e) change no workflow. No ruleset or required check changes: the required check
   stays the job `governance`.
5. Build (b) of SPEC-0051 cites this ADR and not `Covered-by: ADR-0340`, and it names here every
   protected path class it changes.
6. Amendment 147 proposes the matching text of SPEC-0051 rule 11. It is not applied to the spec
   here (principle 6).

## Consequences

CI runs the acceptance check on every commit of a pull request and on the default branch, in the kit
and, through the installed workflow, in a project. The check is cheap: it reads files and git, runs
no evidence and needs no network. With no record the step prints `ok acceptance (0 records)`. The
step passes no saved comments, so until build (c) an `accepted` record fails it under rule 6.

## Residual

- 2026-11-09: until build (c) lands, a project cannot pass this step with an `accepted` record, and
  the step is what enforces that; a project's first acceptance waits for build (c) (due 2026-12-31).

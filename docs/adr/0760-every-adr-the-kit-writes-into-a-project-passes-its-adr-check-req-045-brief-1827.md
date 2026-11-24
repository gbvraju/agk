# ADR-0760: Every ADR the kit writes into a project passes its ADR check (REQ-045, brief #1827)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers
- Related: brief #1827, ADR-0735, ADR-0681, SPEC-0038, SPEC-0072
- Requirements: REQ-045

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

In a clean solo project, `steward_owner.py work-type --yes` wrote `docs/adr/0002-work-type.md`, and the project's own
`check_adrs.py` failed it: `missing field 'Requirements'` and `missing section '## Residual'` (brief #1827, measured on
main at e13f4f53). The playbook draft of `steward_owner.py draft --slug` has the same gap. Every other kit writer of a
project ADR passes, but no test lists the writers, so a new one could ship the same defect.

## Decision

1. `steward_owner.work_type_adr` and `steward_owner.draft` write `- Requirements: REQ-001` after `- Related:` (one
   constant, `ADR_REQUIREMENT`, the value and reason of `wsl.REQUIREMENT`) and a last section `## Residual` with one
   line `- <today>: none; the owner reviews the change before the merge.`. Nothing else in either record changes.
2. `tests/kit/test_kit_adr_writers.py` holds one table of every kit writer of a project ADR, each with a builder from
   invented data, and asserts `check_adrs.validate` passes each. A census finds every writer by its text (a code line of
   `scripts/agk/**/*.py` emitting `# ADR-{` or `"# ADR-`, a `kit/templates/**/*.md` whose first line is `# ADR-`, and
   `docs/adr/TEMPLATE.md`) and fails naming `<file>:<line>` for one the table does not list. The two printed skeletons
   (`upgrade.report` without `--write-adr`, `uninstall.adr_skeleton`) are rows marked `printed` and not validated.
3. The `[[testing.map]]` entry of `scripts/agk/check_adrs.py` in `agk.toml` lists the three tests that now run the
   check (`test_kit_adr_writers.py`, `test_standard_confirm.py`, `test_steward_work_type.py`), as
   `tests/kit/test_always_full_infra.py` requires; no setting changes.

## Consequences

The first owner yes of a solo project no longer opens a red pull request. A field or section later added to
`check_adrs` turns the table red for every writer without it, and a new writer must join the table. A project whose
branch already holds the old Proposed record adds the two parts by hand (the changelog fragment names them).

## Residual

- 2026-11-23: `personal_adopt.adr_text` titles its record `# {aid}:`, which the census text does not match; the table
  lists it by hand and a test keeps that row named. `uninstall.adr_skeleton` still prints no `## Consequences` or
  `## Residual` (Q-1827-3).

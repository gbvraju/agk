# ADR-0151: retired requirements and untagged tests (REQ-039, brief 244 build (a), SPEC-0004 rule 24)

- Status: Accepted
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0025, ADR-0150
- Requirements: REQ-039

Protected classes: `docs/requirements.md`, `kit/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #244 (priority 2, the maintainer's question of 2026-10-26, before a pilot on an existing codebase): AGK makes a change of behaviour update its tests and requires a tagged test for every `done` requirement, but it does not find a test for a dropped feature that still passes, or a test linked to no requirement. Requirements have no `retired` status, so dropping a feature leaves its tests behind silently. This is build (a): retired requirements and untagged tests; build (b), the optional unused-code and coverage commands, is a later build. The tests were written first.

## Decision

1. **`retired` joins the requirement statuses** (`common.ALLOWED_STATUS`: `planned`, `in-progress`, `done`, `retired`). A requirement is retired with an ADR, like any change of a `done` one. The first paragraph of `docs/requirements.md` and of `kit/templates/requirements.md` names the four.
2. **The one new block.** While a requirement is `retired`, a `REQ-nnn` marker for it under the test directories fails `check_requirements.py`: `REQ-nnn: retired requirement still has a test marker in <files>`. It names the requirement and the files and never the test's text. So the pull request that retires a requirement removes its tests or retags them to a requirement they still prove. It falls only on that pull request. A retired requirement needs no marker and no criteria coverage.
3. **Untagged tests** (`common.untagged_test_files`, `drift_audit.d8`). The weekly drift audit adds the finding D8, subject `tests`: `<n> test files carry no requirement marker: <paths>`, up to 20 paths and then `and N more`. The files are those the checks already read for markers (the configured directories and patterns). A file with any `REQ-nnn` token counts as tagged, even one the requirements file lacks (the stray-marker finding D7 covers that). It never blocks, names paths only, and a project with none gets no finding. The summary line of the report carries `D8=<n>`.
4. **Traceability.** `traceability.py` ends, after a blank line, with `Retired: <ids>` and `Untagged test files (<n>): <paths>` when there are any, and is unchanged when there are none.
5. **The guide** (`docs/guides/existing-codebase.md`, step 3) says how to retire a requirement, what D8 lists and that a cleanup pull request declares `Behaviour: unchanged` and keeps the proof green.
6. **Housekeeping the brief asks for:** a local scanner reported the made-up skill name `SECRET_NAME` in `tests/kit/test_engines.py` (B105 reads the variable name as a credential). A `# nosec` comment is a new ignore entry for a scanner, which CLAUDE.md rule 5 forbids, so the variable is renamed `ENGINE_NAME_SHOWN` in every place it is used (the verdict on cfb1c19); its value and what the test checks are unchanged.
7. **Readings taken where the brief leaves a point open** (the most conservative each): "the next free `D` code" is D8, cited as `SPEC-0004 rule 24`; "lists them with a count" is one finding that lists up to 20 paths and counts them all, so an existing codebase with hundreds of untagged files does not flood the audit issue; the facts and the report read a `retired` status as `unknown`, as for any status they do not list (no change to schema 6 or 7; a later brief may show retired requirements there). The facts count the audit's findings by code, so `drift.counts` gains `D8`: `kit/facts-schema.json` lists it as an optional property (schema 1 stays; a document without it still validates) and the goldens of the facts fixtures carry `"D8": 0`. Amendment 86 (`docs/runs/proposed-spec-amendments-86.md`) is applied to SPEC-0010 (new rule 26) and SPEC-0004 (new rule 24, rule 11). Flow mode: fragment `changelog.d/retired-requirements.md`; no version bump.

## Consequences

- Dropping a feature now has a place to be recorded, and the tests that still guard it fail loudly in the pull request that retires it.
- An existing codebase sees its untagged tests listed each week, never blocking.

## Residual

- 2026-10-26: the facts and the report show a `retired` requirement as `unknown` until a brief teaches them the status (due 2026-12-31).

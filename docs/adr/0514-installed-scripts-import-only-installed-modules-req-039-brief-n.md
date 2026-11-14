# ADR-0514: Installed scripts import only installed modules

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0006, SPEC-0044 rule 10, ADR-0052, brief #997, brief #1214, plan #661
- Requirements: REQ-039

## Context

A project installed with `init.py` holds the manifest's installed list of `scripts/agk/`, never the kit-only files
(`init.py`, `adopt.py`; `KIT_ONLY_FILES`). Since brief #997 `scripts/agk/doctor.py` imported `adopt` at module level
for three names of the test walk (`SKIP_DIRS`, `FRONTEND_PATTERNS`, `walked_dirs`). Every project's governance job starts
with `python3 scripts/agk/doctor.py --paused`, so in every installed project that step stopped with
`ModuleNotFoundError: No module named 'adopt'` and every later step reported a failure. `make agk-governance` does not run
the doctor, so local mode never saw it, and the kit's own CI has `adopt.py`.

## Decision

1. The test-walk names (`FRONTEND_PATTERNS`, `SKIP_DIRS`, `KIT_DIRS`, `walked_dirs`) move unchanged to
   `scripts/agk/common.py`, which every project installs. `adopt.py` and `doctor.py` both import them from there, so both
   read one definition; `doctor.py` no longer imports `adopt`. Of the two answers the brief allows, this is the one that
   works: the doctor's front-end and outside-`test_dirs` lines run in projects too, so a lazy import of `adopt` on a
   kit-only path would still fail there.
2. `tests/kit/test_installed_imports.py` holds the rule: each installed `scripts/agk/*.py` (the manifest's installed list
   for `init`, with and without the experimental files) imports at module level only an installed module or the
   standard library; an import of a kit-only module inside a function is allowed only when its line says `kit-only`
   (it is guarded by `ImportError`, or runs only in the kit repository), as the four existing ones do. The same file runs
   `init.py` into a temporary folder and `python3 -I scripts/agk/doctor.py --paused` there, which must exit 0.

## Consequences

The governance job of an installed project passes its first step again. A later module-level import of a kit-only file
fails the kit's own tests before a release. Protected path classes changed: `scripts/agk/` (`doctor.py`, `adopt.py`,
`common.py`) and `tests/kit/` (`test_installed_imports.py`). No workflow, ruleset, `agk.toml` or `.claude/` change.

## Residual

- 2026-11-14: projects already on v0.64.0 keep the failing doctor until they upgrade to the release that carries this
  change (release 0.64.1, brief #1210), which is the maintainers' to tag (due 2026-11-30).

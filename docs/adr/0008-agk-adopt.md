# ADR-0008: agk adopt and the shared-kit changes it needs

- Status: Accepted
- Date: 2026-10-14
- Deciders: maintainers
- Related: ADR-0001, ADR-0007
- Requirements: REQ-010

## Context

SPEC-0002 (Approved) defines `agk adopt` for existing repositories. ADR-0007 moved the kit's commands and
configuration into `agk.mk` and `agk.toml` so that adopt never edits a project's `Makefile` or `pyproject.toml`; this
ADR is the adopt step itself (SPEC-0002 rules 1-4, 7, 9, 11, 13-18, and the adopted-mode templates of rule 12).

Protected classes: `constitution/`, `config/`, `.claude/`, `.github/`, `docs/requirements.md`, `CLAUDE.md`,
`scripts/agk/`, `tests/kit/`, `Makefile`, `pyproject.toml`, `agk.mk`, `agk.toml`, `kit/`, `tests/kit_dev/`. This PR
changes `scripts/agk/`, `tests/kit/`, `kit/` and `tests/kit_dev/`.

## Decision

1. **`scripts/agk/adopt.py`** installs the kit into an existing git work tree: it creates adopt-owned files only when
   absent, appends one marked block to `.gitignore` and, when they exist, to `CLAUDE.md`, `.github/CODEOWNERS` and
   `.github/PULL_REQUEST_TEMPLATE.md`, and refuses (exit 1, nothing written) on any differing created file, changed
   or duplicated block, symlink or unknown default branch. It never writes `Makefile`, `pyproject.toml` or any other
   product file, and never imports, executes or parses target code. Like `init.py` it is kit-only.
2. **Manifest `adopt` section** in `kit/manifest.json`: `skip` (verbatim files adopt does not write: `Makefile`),
   `blocks` (marker style per block-managed file) and `templates` (adopt's own template set).
3. **Adopt templates** in `kit/templates/`: `agk.adopt.toml` (mode `adopt`, empty `project_tests`, detected
   `test_dirs` and `test_patterns`), `protected-paths.adopt.txt` and `reviewers.adopt.yaml` (no `Makefile` or
   `pyproject.toml`), `adr-0001-adopt.md` (no creation-commit claim; lists the project's existing protected-class
   files).
4. **Shared kit changes** (installed verbatim, so kit version `0.4.0`): `common.find_markers` takes the configured
   patterns (`test_patterns`, default `test_*.py`) and leaves `tests/kit` out of the search in adopt mode unless a
   listed directory is inside it; `agk.toml` gains `test_patterns` and `mode`; `reviewers.py --check-codeowners`
   compares only the marked block of a project CODEOWNERS; `init.py` refuses a target installed by adopt.
5. **Detection.** Adopt writes `test_dirs` as the topmost directories holding `*_test.py` or `test_*.py` files (hidden
   directories, `node_modules`, `venv`, `build`, `dist`, `tests/kit` and `scripts/agk` are skipped) and reuses the
   stamped values of an existing adopt install so a second run changes nothing.

## Consequences

- An adopted repository's `make -f agk.mk agk-governance` and `agk-test` pass while its own `make test` and CI are
  untouched; its `project_tests` is empty.
- An init repository installed before this version keeps working: the `pyproject.toml` stamp is still read.
- Maintainers flip the adopted ADR-0001 to Accepted in the adoption PR; a later adopt run on a repository whose ADR
  differs from the template refuses, as init does.

## Residual

- 2026-10-14: no upgrade path between kit versions or between init and adopt (K3).
- 2026-10-14: the live proof on a real codebase is still to be done (SPEC-0002 rule 19).
- 2026-10-14: class naming in an ADR is still a substring match (ADR-0003 residual).

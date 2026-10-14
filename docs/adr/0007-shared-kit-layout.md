# ADR-0007: Shared kit layout: agk.mk, agk.toml, per-mode protected lists

- Status: Proposed
- Date: 2026-10-14
- Deciders: maintainers
- Related: ADR-0004, ADR-0006
- Amends: ADR-0005
- Requirements: REQ-009, REQ-010

## Context

SPEC-0002 (Approved) defines `agk adopt` for existing repositories, which must not edit a project's `Makefile` or
`pyproject.toml`. That needs the kit's commands and settings to live in files of their own, and the same layout is
used by `agk init` and by this repository so that one set of checks and one workflow serve every mode. This ADR is
the shared-kit step (SPEC-0002 rules 5-8, 10 and 12 for init and this repository); `agk adopt` itself follows.
ADR-0005 decision 1 (the `Makefile` `test` target) is amended; ADR-0004 decision 2 (the installed protected list) is
extended without changing ADR-0004's text.

Protected classes: `constitution/`, `config/`, `.claude/`, `.github/`, `docs/requirements.md`, `CLAUDE.md`,
`scripts/agk/`, `tests/kit/`, `Makefile`, `pyproject.toml`, `agk.mk`, `agk.toml`, `kit/`, `tests/kit_dev/`. This PR
changes all of them except `docs/requirements.md` and `pyproject.toml`.

## Decision

1. **`agk.mk`** holds the kit's commands: `agk-governance`, `agk-lint`, `agk-test`, `agk-traceability`. The
   workflow, the stop hook and the settings call `make -f agk.mk agk-<name>`.
2. **`agk.toml`** holds the kit's configuration: `mode`, `version`, `installed`, `default_branch`, `test_dirs`,
   `lint_paths`. The checks read it first and fall back to `[tool.agk]` in `pyproject.toml` (earlier installs); an
   absent key takes its default. `scripts/agk/config.py KEY` prints a value for `agk.mk`.
3. **Thin `Makefile`.** It includes `agk.mk` and aliases `governance`, `lint`, `test` and `traceability`. `test` runs
   the kit tests through `agk-test`, then the project's own tests under `tests/` (`pytest tests`, exit 5 meaning none
   collected counts as success). This amends ADR-0005 decision 1: project tests still run under `make test`.
4. **This repository adopts `agk.mk` and `agk.toml` itself**, because the workflow is verbatim. Its `agk-test` also
   runs `tests/kit_dev` when it exists.
5. **Kit tests run in isolation.** `tests/kit/pytest.ini`, selected with `-c`, replaces project pytest config for
   them. `tests/kit/conftest.py` puts `scripts/agk` on `sys.path` and collects nothing unless `AGK_KIT_TESTS=1`,
   which `agk-test` sets, so a project's own `pytest .` ignores them.
6. **Default branch.** Base resolution is `--base`, `AGK_BASE`, `GITHUB_BASE_REF`, then `origin/<default_branch>` and
   `<default_branch>` from `agk.toml` (default `main`). The workflow runs on `pull_request` and on every `push` and
   gates the job on `github.event.repository.default_branch`, so no branch name is written into it.
   `common.detect_default_branch` reads `.git` files without calling git; init uses it, falling back to `main`, and
   reuses the stamped value on a second run.
7. **Wording.** The words "main" in installed text (`CLAUDE.md`, `constitution/principles.md`, the ADR template)
   become "the default branch".
8. **Lint scope.** `agk-lint` runs `ruff check --isolated` with the kit's rules as flags over `lint_paths`, never over
   product paths.
9. **Per-mode protected lists.** The installed list is the previous ten entries plus `agk.mk` and `agk.toml`,
   rendered from `kit/templates/protected-paths.txt` with the matching `reviewers.yaml` template. This repository's
   list is that plus `kit/` and `tests/kit_dev/`. The adopted-mode list comes with `agk adopt`.
10. **Kit version** is `0.3.0`: installed content changed.

## Consequences

- A repository installed by init at 0.1 or 0.2 keeps working: `[tool.agk]` is still read; upgrading is out of scope.
- The installed `.claude/settings.json` also asks before editing `kit/` and `tests/kit_dev/`, which do not exist in
  a target.
- Kit tests need `AGK_KIT_TESTS=1` (or `make test`) to run; a bare `pytest tests/kit` collects nothing.

## Residual

- 2026-10-14: `agk adopt` and the adopted-mode protected list are not part of this ADR (SPEC-0002 rules 1-4, 9, 11,
  13-20).
- 2026-10-14: no upgrade path between kit versions (K3).
- 2026-10-14: class naming in an ADR is still a substring match (ADR-0003 residual).

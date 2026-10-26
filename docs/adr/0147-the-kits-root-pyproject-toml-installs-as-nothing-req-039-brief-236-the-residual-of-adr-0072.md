# ADR-0147: the kit's root pyproject.toml installs as nothing (REQ-039, brief 236, the residual of ADR-0072)

- Status: Proposed
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0072, ADR-0031
- Requirements: REQ-039

Protected classes: `kit/`, `scripts/agk/`, `tests/kit_dev/`

## Context

Brief #236 (priority 1, measured 2026-10-26 from a hosting provider's build log pasted by the maintainer): a pull-request build that did not detect Node ran `pip install .` at the repository root. The `pyproject.toml` the kit renders there has a `[project]` table and no build system or package list, so setuptools stopped with "Multiple top-level packages discovered in a flat-layout" and the deploy failed before its own command ran. With the file made installable as nothing, the same step read "Successfully installed ... 0.0.0". Every project the kit installs has this file. This closes the residual of 2026-10-22 under ADR-0072 (due 2026-11-30). The tests were written first.

## Decision

1. **The template.** `kit/templates/pyproject.toml` gains `[build-system]` (`requires = ["setuptools>=61"]`, `build-backend = "setuptools.build_meta"`) and `[tool.setuptools]` with `packages = []`; the `[project]` table and the pytest and ruff settings stay.
2. **The upgrade** (`scripts/agk/upgrade.py`, `pyproject_fix`). After init the root file belongs to the project, so the upgrade never rewrites it. For an init install it appends the two tables, and only them, when the file parses, has a `[project]` table that is still the one the template rendered (the keys `name`, `version`, `requires-python` and `dependencies` and no others, `version = "0.0.0"`, `dependencies = []`) and has neither a `[build-system]` table nor a `[tool.setuptools]` table. A `[project]` table of the project's own may build a real package from the root (a `src/` layout with no `[build-system]` builds today by setuptools' auto-discovery), and `packages = []` would empty its wheel without an error (the verdict on 302dee7); the file stays byte for byte and the plan notes how to fix it by hand. Every existing byte stays; a missing final newline gets one, then one blank line, then the tables. The plan names the change (`replace pyproject.toml (adds …)`), and, since `pyproject.toml` is a protected path, prints the protected class and the ADR skeleton as for any protected file. A second run finds the tables and changes nothing.
3. **Left alone, with the most conservative reading each:** a file whose `[project]` table is the project's own (a note: `pyproject-unchanged pyproject.toml the [project] table is the project's own; add [build-system] and [tool.setuptools] packages = [] only if it builds no package`); a file with both tables (nothing to do); a file with only one of them (a note `pyproject-unchanged pyproject.toml has … already; left as it is`, since appending a second `[tool.setuptools]` would break the TOML and a project's own build system is its own); a file that is not valid TOML or has no `[project]` table; a symlink; the `pyproject.toml` of an adopted project, which the kit never installed (`adopt` installs no `pyproject.toml`, so "adopt follows the same rule" is read as: the upgrade does not touch it; Q-236-1 in the pull request); and a `pyproject.toml` that still holds the legacy `[tool.agk]` stamp, which an earlier ruling (Q-K3-71) says is never written: the project removes the stamp in its own change (Q-236-2).
4. **The guide** (`docs/guides/getting-started.md`, "When something goes wrong") says that a host that auto-detects Python at the root now installs nothing, how an earlier install gets the tables, and that a project that deploys a subfolder sets the host's root directory to it.
5. The residual row of 2026-10-22 under ADR-0072 moves to the closed table of `docs/runs/residuals.md`. No spec rule changes, so reserved amendment 83 is not used. Flow mode: fragment `changelog.d/pyproject-installs-as-nothing.md`; no version bump (the release 0.56.0 gathers it).

## Consequences

- A host that runs `pip install .` at the root of a new project, or of an upgraded one, succeeds and installs nothing.
- A project whose own build system sits in a file the upgrade leaves alone keeps its file unchanged and is told so.

## Residual

- 2026-10-26: an adopted project and a legacy-stamp install do not get the two tables from the upgrade; they add them in their own change if their host builds the root (due 2026-12-31).

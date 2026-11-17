# ADR-0620: /agk:setup build (c): native Windows installs through winget at minimum versions, stopping cleanly

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: SPEC-0065, ADR-0618, ADR-0619, ADR-0577, brief #1462, plan #661
- Requirements: REQ-072

## Context

SPEC-0065 (Approved) names eight builds of `/agk:setup` (rule 18); this is build (c): the native Windows path, winget,
the minimum versions and the stop lines (rule 7). Build (a) (ADR-0618) started the minimum-version table with Python
3.11 and Node.js 20 and left the proxy's test download to the builds that download.

## Decision

1. **One table in `setup.py`.** `MINIMUM` gains every tool of brief #1462 answer 1 and `WINGET` names each tool's winget
   package in install order: Python 3.11 (`pyproject.toml`), git 2.43, GitHub CLI 2.45, Node.js 20 (LTS), PowerShell
   7.6, Windows Terminal 1.23, gitleaks 8.30.1 (`common.GITLEAKS_PIN`, CI's pin) and Podman 4.9; Docker and Claude Code
   have no minimum. Each floor is at or below the vendor's current release, read once on 2026-11-17 (git 2.55, GitHub
   CLI 2.95, PowerShell 7.7 with 7.6 its oldest supported line, Windows Terminal 1.24, Podman 5.8, gitleaks at CI's
   pin), and at or below what Ubuntu 24.04 ships (git 2.43, GitHub CLI 2.45, Podman 4.9), so build (e)'s distribution
   packages meet the same table `(verify)`. A newer floor is a later change to this one table. Claude Code is installed by its own installer (`CLAUDE_INSTALL`)
   `(verify: the Windows installer command)`.
2. **`setup.py install`** (native Windows only; any other platform is refused by name and nothing runs). Checked before:
   a tool missing or older than its minimum is to install; the container engine only when the project uses containers
   and no Docker is present. Without `--yes` nothing runs (rule 5). Before the first install, and only when a winget
   tool is to install: winget missing or refused by its App Installer policy, no administrator right, or a refused test
   download (`winget show` of the first package) stops with one line naming what IT must allow and the tools to install
   by hand. Each install is one `winget install --id <package> --exact --source winget` with the agreements accepted on
   the person's yes; checked after through `winget list` (this process's PATH is not refreshed by an install). A
   failed install or a version still below the minimum marks the step `failed`, stops the run and runs nothing after
   it; winget's own transaction leaves that tool as it was. A second run on a set-up machine installs nothing.
3. **A kit-only bootstrap, `scripts/agk/setup_windows.ps1`**, for a machine with no Python to run `setup.py`: it reads
   Python's minimum and package from `setup.py`'s table as text, holds none of its own, applies the same four stops
   before its one install, installs Python alone through winget on `-Yes`, then hands every other tool to
   `setup.py install`. It is named in `tests/kit_dev/test_kit_manifest.py`'s kit-only list, where the code keeps that
   list (the brief names `kit/manifest.json`).

## Consequences

A native Windows machine with nothing installed reaches every tool of the table with one yes, or stops before any
change with one line IT can act on. Protected path classes changed: `scripts/agk/` (`setup.py`, `setup_windows.ps1`),
`tests/kit/` (`test_setup_windows.py`), `tests/kit_dev/` (`test_kit_manifest.py` lists the kit-only file) and
`agk.toml` (the `[[testing.map]]` entries). No workflow, ruleset, required check or secret changes; CI mode installs
nothing.

## Residual

- 2026-11-17 (verify): `setup.py install` and `setup_windows.ps1` have not run on native Windows; the pull request
  reports `Verified: (verify) run on Windows` until a person runs it (due 2027-03-31).
- 2026-11-17 (verify): the winget package names, the Claude Code installer command and the `winget list` output shape
  the after-check reads are not confirmed on a Windows machine (due 2027-03-31).
- 2026-11-17: the skill `skills/setup/SKILL.md` does not yet call the install form; the brief's `Touches:` leaves it
  out, and build (d) wires the platform paths into the skill.

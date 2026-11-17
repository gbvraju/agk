# ADR-0622: /agk:setup build (e): Linux and cloud virtual machines install through apt or dnf, and macOS gets one line

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: SPEC-0065, ADR-0618, ADR-0619, ADR-0620, ADR-0577, ADR-0608, brief #1464, plan #661
- Requirements: REQ-072

## Context

SPEC-0065 (Approved) names eight builds of `/agk:setup` (rule 18); this is build (e): Linux and cloud virtual
machines, and macOS's one line (rule 7). Build (c) (ADR-0620) filled the one minimum-version table in `setup.py` and
added `setup.py install` for native Windows; rule 7 asks the Linux path to meet the same table with the
distribution's packages, and Node.js and Claude Code by the path `wsl_setup.ps1`'s embedded steps use.

## Decision

1. **`setup.py install` takes the platform from the machine read.** Native Windows keeps build (c)'s path; Linux
   (a cloud virtual machine, or a Linux machine in local mode) takes the new path; macOS prints one line
   (`MAC_LINE`), exits 1 and changes nothing (`Q-S0065-3`); any other platform is still refused by name. The
   machine read gains `package_manager` (`apt`, `dnf` or `absent`) and `sudo` (ready only when `sudo -n true`
   passes: sudo present but refused, or asking for its sign-in with no terminal, is not ready).
2. **The Linux path, at the one table's minimums.** Checked before: git, GitHub CLI, Node.js, gitleaks and Claude Code,
   and Podman only when the project uses containers and no Docker is present; Python is the interpreter running
   `setup.py`, so it is read and skipped. git, GitHub CLI and Podman are the distribution's packages
   (`LINUX_PACKAGES`, `apt-get install -y -q` or `dnf install -y -q`, through `sudo` when the account is not root);
   Node.js is NodeSource's setup script then the `nodejs` package (`NODE_SETUP`, wsl_setup.ps1's path); gitleaks is
   CI's pin (`common.GITLEAKS_PIN`) from its release, checked against its published checksum file (ADR-0608's
   path); Claude Code is its own installer (`CLAUDE_LINUX`, as wsl_setup.ps1 runs it) as the user. Without `--yes`
   nothing runs. Before the first install: no apt nor dnf (when a package or Node.js is to install), an account that
   is not root and whose sudo is not ready (when any step but Claude Code's user install is to install; the line names
   `sudo -v`), or a refused test download (the package lists' refresh, when a package or Node.js is to install) stops
   with one line naming what to allow and the tools to install by hand. Each install is checked after on the PATH with the installers' folders; a failure or a version still below
   the minimum is `failed`, stops the run, and runs nothing after it, the package manager's transaction leaving that
   tool as it was. A second run installs nothing. Build (b)'s proposal of `launch_adapter = "bash
   scripts/start-session-local.sh"` on Linux in local mode is the background adapter of rule 10, unchanged.
3. **A kit-only bootstrap, `scripts/agk/setup_linux.sh`**, for a machine without Python 3.11 or curl: it reads
   Python's floor from `setup.py`'s table as text, applies the same stops, installs `python3`, `curl` and
   `ca-certificates` alone on `--yes`, then runs `setup.py install --root <the project's folder>`. It also holds the
   three non-package steps (`node`, `gitleaks`, `claude`), each called by `setup.py` with its version or URL, so the
   script holds no version and no URL of its own but gitleaks' release folder. On macOS it prints `MAC_LINE` word for
   word. It is named in `tests/kit_dev/test_kit_manifest.py`'s kit-only list, where the code keeps that list.

## Consequences

A Linux or cloud machine with nothing but a shell reaches every tool of the table with one yes, or stops before any
change with one line; a Mac is told it is not covered and nothing changes. Protected path classes changed:
`scripts/agk/` (`setup.py`, `setup_linux.sh`), `tests/kit/` (`test_setup_linux.py`, and `test_setup_windows.py`,
whose refused platform is now one with no path), `tests/kit_dev/` (`test_kit_manifest.py` lists the kit-only file) and
`agk.toml` (the `[[testing.map]]` entries). No workflow, ruleset, required check or secret changes; CI mode installs
nothing.

## Residual

- 2026-11-17 (verify): `setup.py install` on Linux and `setup_linux.sh` have not run on a real Linux or cloud
  machine; the pull request reports `Verified: (verify) run on Linux` until a person runs it (due 2027-03-31).
- 2026-11-17 (verify): the dnf NodeSource URL, and that Debian 12's and older distributions' git and Podman packages
  read below the table (a `failed` row, not a silent pass), are not confirmed on those machines (due 2027-03-31).
- 2026-11-17: when NodeSource's setup script has added its package source and the `nodejs` install then fails, that
  source stays; the `failed` row says so, and removing it is left to the person, since its file names are the
  script's own `(verify)` (due 2027-03-31).
- 2026-11-17: the skill `skills/setup/SKILL.md` does not yet call the install form; build (d) wires the platform
  paths into the skill, as ADR-0620's residual says.

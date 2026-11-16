# ADR-0579: Docker is a choice of container engine beside Podman

- Status: Accepted
- Date: 2026-11-16
- Deciders: maintainers
- Related: ADR-0577, brief #1379, brief #1376, plan #661
- Requirements: REQ-050

## Context

`/agk:wsl` (ADR-0577) installs Podman inside WSL 2 and nothing else. Many projects use Docker and Compose files.
Docker Engine on Linux and inside WSL 2 is open source; Docker Desktop on Windows has its own WSL integration and a
licence that may need a paid subscription for larger organisations (verify: Docker's current terms, read from
Docker's own page). The owner asked for the same setup with Docker, without gaps (brief #1379). The brief says
#1376 already compares Podman's versions, lists its volumes and stops its Windows machine; the merged code does none
of these, so this ADR adds them for whichever engine is chosen, Podman included.

## Decision

1. **The engine is chosen, Podman the default.** `wsl.py engine` reads the project's compose files, `Dockerfile`,
   `Containerfile` and scripts that call `docker` or `podman` (the kit's own `scripts/agk/` never counts) and the
   engines on this machine, and prints the one it recommends with its reason in one line; the person may choose
   `podman`, `docker` (Docker Engine inside WSL) or `docker-desktop` (Docker Desktop's WSL integration). Podman is
   the default when nothing decides. `wsl_setup.ps1 -Engine <engine>` sets up the choice.
2. **Docker Engine** comes from Docker's own apt repository for the distribution (`docker-ce`, `docker-ce-cli`,
   `containerd.io`, `docker-buildx-plugin`, `docker-compose-plugin`, `docker-ce-rootless-extras`; verify: the names
   on Docker's install page). The person's user joins the `docker` group, with one line that this grants
   root-equivalent access on that machine, or, with `-DockerRootless`, Docker's rootless mode
   (`dockerd-rootless-setuptool.sh install`) and no group. systemd starts the daemon.
3. **Docker Desktop is detected, never installed.** When it is present, `wsl.py engine` names it, says in one line
   that its licence may need a subscription for the organisation and points to Docker's page, stating no terms, and
   offers its WSL integration for the workforce's distribution or Docker Engine inside WSL with Desktop's engine
   stopped. Two engines never share the ports: the step `one_engine` stops the run while Desktop runs and Docker
   Engine is chosen.
4. **The same checks for every engine:** the engine's version on Windows and in WSL (`engines` in the `-Json`
   table, the status line `engine:`); the volumes listed read-only with their export and import commands, nothing
   moved; the Windows engine stopped on the pass after the adapter pull request merges (`windows_engine`), never
   uninstalled or removed; `-Back` starts it again (`windows_engine_back`), stopping Docker Engine inside WSL first.
5. **The check starts one container and one compose service** with the chosen engine (`engine_check`). A project
   whose scripts call `docker` keeps working with Podman only with `podman-docker`, which the engine lines name.

## Consequences

A Docker project moves into WSL with Docker Engine and the same checks a Podman project gets. Protected path classes
changed: `scripts/agk/` (`wsl.py`, `wsl_setup.ps1`), `skills/` (`skills/wsl/SKILL.md`), `tests/kit/`
(`test_wsl_docker.py`, and `test_wsl_setup.py` reads the status line `engine:` where it read `podman:`) and
`agk.toml` (the new test in the `[[testing.map]]` entries). No workflow, ruleset or required check changes; CI mode
is not applicable, as GitHub's runners carry Docker already.

## Residual

- 2026-11-16 (verify): the setup has not run with Docker; the pull request reports `Verified: (verify) run with
  Docker` until a person runs it once.
- 2026-11-16 (verify): `podman machine list --format '{{.Running}}'`, the Docker Desktop path
  `%ProgramFiles%\Docker\Docker\Docker Desktop.exe` and its process name `Docker Desktop` are read from the vendors'
  usual layout, not confirmed on a machine.
- 2026-11-16: `/agk:setup` is not on the default branch; the engine choice there follows when it is built
  (Q-1379-1). On Linux without WSL, `wsl.py engine` prints the same lines; the install there waits for `/agk:setup`.

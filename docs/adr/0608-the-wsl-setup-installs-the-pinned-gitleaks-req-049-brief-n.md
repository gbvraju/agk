# ADR-0608: The WSL setup installs the pinned gitleaks

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: ADR-0577, ADR-0306, ADR-0327, ADR-0158, brief #1450, plan #661
- Requirements: REQ-049

## Context

`prepush.py`'s secret scan and the personal floor need gitleaks on the PATH and fail until it is there. The WSL setup
of ADR-0577 (`scripts/agk/wsl_setup.ps1`) installs git, Python, the GitHub CLI, Node.js, Claude Code and a container
engine, but not gitleaks, so every new WSL machine failed its first local-mode push (brief #1450).

## Decision

1. **One more step, `gitleaks`,** in the setup's root script right after `packages`: it checks that `gitleaks version`
   equals the pinned version, else installs that release for the machine's architecture (`x86_64` as `x64`,
   `aarch64` as `arm64`; any other architecture fails the step) into `/usr/local/bin`, then checks again. An older
   version is replaced; the pinned one is skipped; `-Status` only checks.
2. **One pin:** the version is read from `GITLEAKS_PIN` in `scripts/agk/common.py`, which a test already keeps equal to
   the governance workflow's pin (ADR-0306); the script never types it. A pin it cannot read fails the step.
3. **A checked download:** the release archive and the release's checksum file are downloaded to a temporary folder,
   and the archive's SHA-256 is compared with its line in that file before anything is unpacked. A blocked download or
   a mismatch fails the step with one line (what to allow, or the mismatch) and installs nothing.
4. **Behind a company proxy** the download uses the system certificate store, into which the setup's `company_ca` step
   already puts the certificate of `-CorpCaFile`; the failure line names `-CorpCaFile`.
5. **The doctor:** inside WSL, a missing gitleaks ends the secret-scan line with
   `run /agk:wsl again; it installs gitleaks <version>`; elsewhere the line is unchanged.
6. **By mode:** local and personal mode in WSL gain the step; hosted mode (the workflow installs its own pinned
   gitleaks) and native Windows (SPEC-0065 build (c)) are unchanged.

## Consequences

A new WSL machine can run its secret scan on its first push. Protected path classes changed: `scripts/agk/`
(`wsl_setup.ps1`, `wsl.py` lists the step, `doctor.py`), `tests/kit/` (`test_wsl_gitleaks.py`), `skills/`
(`skills/wsl/SKILL.md` names the step among those a certificate can fail) and `agk.toml` (the new test in the
`[[testing.map]]` entries). No workflow, ruleset or required check changes.

## Residual

- 2026-11-17 (verify): `wsl_setup.ps1` has not run on Windows; the pull request reports `Verified: (verify) run on
  Windows` until the owner runs it once.
- 2026-11-17 (verify): the release file names `gitleaks_<v>_linux_arm64.tar.gz` and `gitleaks_<v>_checksums.txt`
  follow the release's naming as the workflow's `linux_x64` archive does; they were not read from the release page.
- 2026-11-17 (verify): the PowerShell parser test is skipped where `pwsh` is not on the runner.

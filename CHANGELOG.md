# Changelog

The changes to the kit of this repository, newest first. In flow mode a build pull request adds one line under `## Unreleased`; a release pull request moves the lines under the new version (SPEC-0028). The history before 0.54.0 is in the git log and in `docs/runs/`.

## Unreleased

- #167 engines: `[engines]` in `agk.toml` and five `doctor` checks that report each engine as present, absent or missing (SPEC-0029 rules 1 to 3, REQ-036)

## 0.54.0 (2026-10-24)

- #165 flow mode: a kit build adds a changelog line instead of bumping the version, one release pull request bumps it, and `check_release.py` checks that pull request

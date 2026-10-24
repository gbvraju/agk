# Changelog

The changes to the kit of this repository, newest first. In flow mode a build pull request adds one line under `## Unreleased`; a release pull request moves the lines under the new version (SPEC-0028). The history before 0.54.0 is in the git log and in `docs/runs/`.

## Unreleased

- #172 `check_brief.py` checks the shape of a brief, and `session.py watch` ends with `conflict #N` when the pull request conflicts with its base (REQ-037 rule 4 and the verdict on #169)
- #173 stack: `/agk:stack` writes one Proposed ADR of two or three stack options with checked and judged practices, and `engines.py stack-check` checks its shape (SPEC-0029 rule 5, REQ-036)
- #170 vision: `/agk:vision` keeps the idea unchanged and the charter records ten answers (SPEC-0029 rule 4, REQ-036)
- #169 session rules and `session.py`: `watch` ends on a verdict, a merge or a close, `next` takes the first free brief (REQ-037 rules 1 to 3 and 5)
- #168 engines: `[engines]` in `agk.toml` and five `doctor` checks that report each engine as present, absent or missing (SPEC-0029 rules 1 to 3, REQ-036)

## 0.54.0 (2026-10-24)

- #165 flow mode: a kit build adds a changelog line instead of bumping the version, one release pull request bumps it, and `check_release.py` checks that pull request

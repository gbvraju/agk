# ADR-0004: Protected list expansion, kit-only paths, neutral CLAUDE.md

- Status: Proposed
- Date: 2026-10-14
- Deciders: maintainers
- Related: ADR-0001, ADR-0003
- Requirements: REQ-001, REQ-005, REQ-009

## Context

SPEC-0001 (Approved) defines `agk init`. Installing the kit means installing its law, and that law must be
protected in the target as it is here. This PR also adds installer sources (`kit/`) and installer tests
(`tests/kit_dev/`), and the installed `CLAUDE.md` must carry no day or milestone references. This ADR amends no
text of ADR-0001 or ADR-0003; it adds decisions.

Protected classes: `constitution/`, `config/`, `.claude/`, `.github/`, `docs/requirements.md`, `CLAUDE.md`,
`scripts/agk/`, `tests/kit/`, `Makefile`, `pyproject.toml`, `kit/`, `tests/kit_dev/`. This PR changes
`config/`, `.claude/`, `.github/`, `CLAUDE.md`, `scripts/agk/`, `tests/kit/`, `Makefile`, `pyproject.toml`,
`kit/` and `tests/kit_dev/`.

## Decision

1. **Protected list expansion.** `config/protected-paths.txt` and the `protected` class of
   `config/reviewers.yaml` add `scripts/agk/`, `tests/kit/`, `Makefile` and `pyproject.toml`. A change to the
   checks, their tests or the build files now needs an ADR that names the class.
2. **Kit-only paths.** `kit/` (manifest and templates) and `tests/kit_dev/` (installer tests) are protected in
   this repository and are added to the `kit` reviewer class. They are never installed in a target. The installed
   protected list is the expansion of decision 1 only, rendered from `kit/templates/protected-paths.txt`; this
   repository's list is that template plus `kit/` and `tests/kit_dev/`.
3. **Neutral CLAUDE.md.** `CLAUDE.md` is installed verbatim, so its rules text drops the day reference and keeps the
   same rules, order and compaction-recovery block.
4. **Settings.** `.claude/settings.json` asks before editing every entry of this repository's protected list
   (`Edit(/path)` rules), and still allows only `Bash(git push -u origin HEAD)` for pushing.
5. **CODEOWNERS.** `.github/CODEOWNERS` is re-rendered from `config/reviewers.yaml` (ADR-0003 decision 3).
6. **Installer.** `scripts/agk/init.py`, `kit/manifest.json` and `kit/templates/` implement SPEC-0001.

## Consequences

- A target cannot loosen its own checks without a visible, reviewed ADR.
- The installed `.claude/settings.json` also lists `Edit(/kit/**)` and `Edit(/tests/kit_dev/**)`, which match
  nothing in a target.
- `tests/kit/` carries markers for kit-defined ids; targets define their own from `REQ-101` (SPEC-0001 rule 11).

## Residual

- 2026-10-14: approved specs are not yet protected by a check; follow-up after this PR (principle 6).
- 2026-10-14: class naming in an ADR is still a substring match (ADR-0003 residual).

# Run report: day 6 (PR #13, agk adopt)

Date: 2026-10-14 (from `date -u`). Implements SPEC-0002 rules 1-4, 7, 9, 11, 13-18 and the adopted-mode templates of
rule 12 (ADR-0008). The live proof on a fork (rules 19-20) is a separate step.

## Decisions taken

- Adopt is kit-only like init; the manifest gains an `adopt` section (`skip`, `blocks`, `templates`); adopt writes
  no `Makefile` or `pyproject.toml` and appends one marked block to `.gitignore`, `CLAUDE.md`, CODEOWNERS and the
  PR template.
- Shared kit changes (kit 0.4.0): marker patterns and the adopt-mode exclusion of `tests/kit`, a CODEOWNERS block
  check, `init` refusing an adopt install.
- Deviations from the Approved specs were proposals (`proposed-spec-amendments-3.md`); applied here on maintainers'
  instruction.

## Questions and reviewer rulings

- Q-K2-12 (adopt scans `agk.toml` `mode` and the `[tool.agk]` header as text, and parses its own `agk.toml`): accepted.
- Q-K2-13 (`test_dirs = ["."]` for a root-level test file; `tests/kit` excluded in adopt mode): accepted.
- Q-K2-14 (the adopted ADR lists only project files adopt does not write; a rerun after the ADR is edited refuses,
  as init does): accepted.

## Reviewer's run on a real clone

Reported by the reviewer: adopt run on a real colorama clone changed only `.gitignore` (by the block); the 8 checks
were green; 0 kit tests appeared in the project's collection; a second run was idempotent. This agent did not run
adopt on any real codebase.

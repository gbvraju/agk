# Run report: day 5, item 2 (PR #11, K2 survey and SPEC-0002)

Date: 2026-10-14 (from `date -u`). Docs only: `docs/runs/k2-target-survey.md`, `docs/specs/0002-agk-adopt.md`
(Draft), this file.

## Decisions taken (each is a numbered rule in the spec)

- Zero-touch: the kit's commands move to `agk.mk` and its settings to `agk.toml`; `Makefile` and `pyproject.toml`
  of a target are never written (rules 4-6).
- Default branch from `.git` files without calling git; shared fix in `common.py` and the workflow, so init gets it
  too (rules 7-8).
- Test discovery by `test_dirs` and `test_patterns`; kit lint by flags over kit paths only (rules 9-10).
- Existing files: one marked block for `.gitignore`, `CLAUDE.md`, `CODEOWNERS`, PR template; refuse on an existing
  `.claude/settings.json` (rule 11).
- Adopted ADR-0001 makes no creation-commit claim (rule 12).
- Init and adopt refuse each other's installs (rule 16).
- Safety rules for the fork recorded as rule 19.

## Questions

- Q-K2-1: introduce `agk.mk` and `agk.toml` in the shared kit (init too; ADR-0007; kit 0.3.0; thin `Makefile` alias in
  init installs) rather than an adopt-only fork of the layout. Recommendation: shared, so one set of checks and one
  workflow serve both modes.
- Q-K2-2: should the project's own `pytest .` collect the kit's `tests/kit`? The target's `lint_python.yml:22` runs
  `pytest .`. Spec default: no, kit tests are collected only through `agk.mk`.
- Q-K2-3: in an adopted repository the whole `.github/` becomes protected (existing workflows included). Spec default:
  keep `.github/` whole (CI is law); alternative: protect only `governance.yml`.
- Q-K2-4: an existing `.claude/settings.json` is refused in K2 (no JSON merge). Accept?
- Q-K2-5: existing `CLAUDE.md`, `CODEOWNERS` and PR template get an appended marked block (spec default) instead of
  refusal. Accept?
- Q-K2-6: reading the default branch by parsing `.git/refs/remotes/origin/HEAD` and `.git/HEAD` is not a git call but
  is coupled to the on-disk format; a packed or absent `origin/HEAD` refuses. Accept?
- Q-K2-7: replacing "main" with "the default branch" in installed text changes `constitution/principles.md`
  (principle 3) and `CLAUDE.md`, both protected, by ADR-0007. Accept?
- Q-K2-8: the checks need Python 3.11 while the target supports 3.9 (`pyproject.toml:12`); CI uses 3.12. Accept the
  local-run limit (residual in the spec)?

## Not done here

- Nothing of the target was run; `agk init`/`adopt` were not run on it; no fork exists yet; no PR was opened on
  `tartley/colorama`.

## Verified

See the PR body.

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
- Adopted ADR-0001 makes no creation-commit claim (rule 13).
- Init and adopt refuse each other's installs (rule 17).
- Safety rules for the fork recorded as rule 20.
- Per-mode protected lists, each rendered from its own template (rule 12, reviewer fix 1).
- The agk repository adopts `agk.mk` and `agk.toml` itself, its `Makefile` becoming thin aliases, covered by ADR-0007
  (rule 5, reviewer fix 2).
- The proof plan adds that a bare `pytest .` in the target collects no `tests/kit` test (rule 18, reviewer fix 3).

## Questions and reviewer rulings

- Q-K2-1: shared kit (`agk.mk`, `agk.toml`; init too). Ruling: shared, ADR-0007, kit 0.3.0.
- Q-K2-2: the project's `pytest .` collecting `tests/kit`. Ruling: no.
- Q-K2-3: protected scope in adopted repositories. Ruling: all of `.github/`.
- Q-K2-4: existing `.claude/settings.json` refused (no JSON merge). Ruling: accepted as the spec default.
- Q-K2-5: existing `CLAUDE.md`, `CODEOWNERS`, PR template get an appended marked block. Ruling: accepted as the spec
  default.
- Q-K2-6: default branch read from `.git` files without calling git. Ruling: accepted as the spec default.
- Q-K2-7: "main" becomes "the default branch" in installed text, by ADR-0007. Ruling: accepted as the spec default.
- Q-K2-8: Python 3.11 needed to run the checks locally. Ruling: accepted as the spec default (spec Residual).

## Not done here

- Nothing of the target was run; `agk init`/`adopt` were not run on it; no fork exists yet; no PR was opened on
  `tartley/colorama`.

## Verified

See the PR body.

## Spec status

- SPEC-0002 set to `Approved` on maintainers' clearance. From now on deviations go into
  `docs/runs/proposed-spec-amendments-2.md`, never into direct edits of the spec. Implementation is split: PR #12
  (ADR-0007, shared kit: rules 5-8, 10 and 12 for init and the agk repository itself, kit 0.3.0) and PR #13 (adopt:
  everything else), the latter opened only after PR #12 merges and maintainers say go.

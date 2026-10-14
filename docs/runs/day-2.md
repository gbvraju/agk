# Run report: day 2 (PR #5, spec for agk init)

Date: 2026-10-14 (from `date -u`). Docs only: `docs/specs/0001-agk-init.md` and this file.

## Decisions taken (each is a numbered rule in the spec)

- Manifest plus templates, not a copied `kit/` tree: the verbatim set points at the kit's own files, so law and tests
  cannot diverge; only project-specific text is duplicated (rules 6–9).
- Init writes nothing until every conflict check has passed; it never overwrites; equal files are unchanged (rules 15–17).
- Dates: first run from the UTC clock, later runs read `[tool.agk] installed`, so a second run is byte-identical (rule 14).
- `tests/kit/` is installed so `make test` is green in the target (rule 18).
- Init does not need git in TARGET, never calls git or gh, and refuses under Python 3.11 (rules 3–4).
- Seeded REQ-001..003 are `planned`; init marks nothing done (rule 11).

## Questions (continuing from Q-K1-1..4, all closed) and reviewer rulings

- Q-K1-5 placeholder team `@REPLACE-ME`: ruled warn only; residual for `agk doctor` recorded in the spec.
- Q-K1-6 marker collision: ruled reservation (`REQ-001..099` kit ids, project ids from `REQ-101`); rule 22 adds that a
  marker for an undefined id never fails a check.
- Q-K1-7 `kit/` protected: ruled yes (ADR-0004 in PR #6; installed list also gains `scripts/agk/`, `tests/kit/`,
  `Makefile`, `pyproject.toml`, rule 21).
- Q-K1-8 initial statuses: ruled conservative (`Proposed`, `planned`); maintainers flip ADR-0001 in the proof PR.
- Q-K1-9 refusal scope and Q-K1-10 inherited action tags / gitleaks licence note: accepted; recorded as residuals.
- Q-K1-11 (new): is `tests/kit_dev/` a protected path in the kit (like `tests/kit/`)? Not in the ruling; the spec
  leaves it unprotected. Recommendation: protect it in ADR-0004, since it guards the installer.
- Q-K1-12 (new): `config/protected-paths.txt` is now a template (kit list = installed list plus `kit/`) instead of a
  verbatim copy, so the kit can protect `kit/` without installing it. Confirm.

## Changes after review of the first commit

- First commit had wrong cross-references between rules (fixed in the second commit).
- Fix list: new rule 21 (installed protected list), kit-only tests in `tests/kit_dev/` (rules 7, 18, 23), rule 20
  covers verbatim files with a CLAUDE.md note, new rule 22 (undefined marker ids), rulings applied.

## Verified

- Docs only; `make governance`, `make test` and `ruff check .` results are in the PR body.

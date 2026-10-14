# Proposed spec amendments 2

Date: 2026-10-14 (from `date -u`). Found while implementing SPEC-0002 rules 5-8, 10 and 12 (ADR-0007) and from the
review of that PR. Approved specs change only through a proposal like this one (principle 6).

**Status: applied on maintainers' instruction, in the same PR as this file (PR #12).** The texts of
`docs/specs/0001-agk-init.md` and `docs/specs/0002-agk-adopt.md` now carry every item below.

## SPEC-0002 (`docs/specs/0002-agk-adopt.md`)

1. **Rule 5, optional keys.** `agk.toml` keys a repository does not need may be omitted. This repository's `agk.toml`
   carries no `mode`, `version` or `installed` (it is not an installed target). `test_patterns` arrives with rule 9
   in the adopt step.
2. **Rule 5, `scripts/agk/config.py`.** A small helper prints one configuration value so `agk.mk` can read
   `lint_paths` and `project_tests`. It is installed verbatim.
3. **Rule 5, `project_tests` and `agk-project-test`.** (Review fix.) `agk.toml` key `project_tests` is a shell command:
   for init the project's pytest command with exit 5 (nothing collected) treated as success, for adopt empty. The
   target `agk-project-test` runs it, or prints a notice when it is empty. The workflow runs it after "Tests of the
   checks", and the thin `Makefile` `test` runs `agk-test` then `agk-project-test`. This keeps ADR-0005 (project
   tests run under `make test` and in CI) after the move to `agk.mk`; a test shows that a failing `tests/test_p.py`
   in an init repository fails the CI steps.
4. **Rule 5, `agk-test`.** `agk-test` also runs `tests/kit_dev` when that directory exists (this repository only).
5. **Rule 7, used by init.** The default-branch detection is used by init too, falling back to `main` instead of
   refusing; adopt keeps the refusal. Init reuses the stamped `default_branch` from an existing `agk.toml`.
6. **Rule 8, ADR template.** The installed ADR-0001 template uses `{{default_branch}}`;
   `kit/templates/branch-rules.txt` keeps its text (it mirrors this repository's immutable ADR-0001) and init prints
   the detected branch above it.

## SPEC-0001 (`docs/specs/0001-agk-init.md`)

1. **Rule 8, variables.** Templates may also use `{{default_branch}}`; the template set gains `agk.toml`.
2. **Rule 14, stamp (Q-K2-11).** `agk.toml` carries the stamp (`mode`, `version`, `installed`, `default_branch`,
   `test_dirs`, `lint_paths`, `project_tests`) and is authoritative. New installs write **no** `[tool.agk]` table in
   `pyproject.toml` (the mirror proposed earlier is dropped); the read fallback to `[tool.agk]` stays for older
   installs, and a second run reads the date from `agk.toml` first, then from that fallback. Tests cover both.
3. **Rules 7, 18 and 21.** The verbatim set gains `agk.mk`, `scripts/agk/config.py` and `tests/kit/pytest.ini`; the
   `Makefile` is the thin aliases file; `make test` runs the kit tests and then the project's tests (item 3 above);
   the installed protected list gains `agk.mk` and `agk.toml`.

## Accepted questions

- Q-K2-9 (thin `Makefile` and exit 5) and Q-K2-10 (`agk.toml` without a stamp in this repository, `test_patterns`
  later) accepted by the reviewer; Q-K2-11 (drop the `[tool.agk]` mirror) accepted as item 2 above.

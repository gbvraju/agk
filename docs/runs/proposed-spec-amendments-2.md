# Proposed spec amendments 2

Date: 2026-10-14 (from `date -u`). Found while implementing SPEC-0002 rules 5-8, 10 and 12 (ADR-0007). Approved
specs change only through a proposal like this one (principle 6). Nothing here is applied to a spec; maintainers
decide.

## SPEC-0002 (`docs/specs/0002-agk-adopt.md`)

1. **Rule 5, optional keys.** The `agk.toml` keys other than the ones a repository needs may be omitted. This
   repository's `agk.toml` carries no `mode`, `version` or `installed` (it is not an installed target). `test_patterns`
   is not implemented in the shared-kit step; it arrives with rule 9 in the adopt step.
2. **Rule 5, `scripts/agk/config.py`.** A small helper prints one configuration value so `agk.mk` can read
   `lint_paths` (rule 10). It is installed verbatim.
3. **Rule 5, `agk-test` and the Makefile `test` target.** `agk-test` also runs `tests/kit_dev` when that directory
   exists (this repository only). The thin `Makefile` `test` target runs `agk-test`, then `pytest tests
   --ignore=tests/kit_dev`, treating pytest exit 5 (nothing collected) as success, so a fresh installed repository
   with no project tests is green.
4. **Rule 7, used by init.** The default-branch detection (`common.detect_default_branch`) is used by init as well,
   falling back to `main` instead of refusing; adopt keeps the refusal (adopt step). Init also reuses the stamped
   `default_branch` from an existing `agk.toml` so a second run is unchanged.
5. **Rule 8, ADR template.** The installed ADR-0001 template names the default branch with a template variable
   `{{default_branch}}`; `kit/templates/branch-rules.txt` keeps its text (it mirrors this repository's ADR-0001,
   which is immutable) and init prints the detected branch above it.

## SPEC-0001 (`docs/specs/0001-agk-init.md`)

1. **Rule 8, variables.** Templates may also use `{{default_branch}}`.
2. **Rule 14, stamp.** `agk.toml` carries the stamp (`mode`, `version`, `installed`, `default_branch`) and is
   authoritative; the `[tool.agk]` stamp in the installed `pyproject.toml` stays as a mirror (version, installed,
   test_dirs) so earlier tooling keeps working. A second run reads the date from `agk.toml` first.
3. **Rules 7, 10 and 18, file list and test target.** The verbatim set gains `agk.mk`, `scripts/agk/config.py` and
   `tests/kit/pytest.ini`; the templates gain `agk.toml`; the `Makefile` is the thin aliases file; `make test` runs
   the kit tests and then the project's tests (see SPEC-0002 amendment 3). Rule 21's installed list gains `agk.mk`
   and `agk.toml`.

## Status

Proposed. Not applied.

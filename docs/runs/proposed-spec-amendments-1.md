# Proposed spec amendments 1 (SPEC-0001)

Date: 2026-10-14 (from `date -u`). Approved specs are changed only through a proposal like this one (principle 6).

## Amendment 1 — rule 18, tests directories

**Reason.** Found while preparing the live proof: with `testpaths = ["tests/kit"]` and a `Makefile` test target that
ran only `tests/kit`, an installed repository's `make test` never ran the project's own tests, so a project could
add tests under `tests/` and see them ignored.

**Old text (rule 18, last sentence).** The `Makefile` `test` target runs the existing ones of `tests/kit` and
`tests/kit_dev` (`$(wildcard ...)`), so the kit's `make test` runs both and the target's runs `tests/kit`.

**New text (rule 18).**

> 18. **Tests directories.** `tests/kit/` (tests of the checks) is installed so the target can test its own checks
> and `make test` is green. The kit-only tests, `tests/kit_dev/test_init.py` and
> `tests/kit_dev/test_kit_manifest.py`, are not installed. The `Makefile` `test` target runs
> `$(PY) -m pytest tests -q`, and `testpaths` in `[tool.pytest.ini_options]` is `["tests"]` in the kit's and the
> installed `pyproject.toml`. The kit's `make test` therefore runs `tests/kit` and `tests/kit_dev`; an installed
> repository's runs `tests/kit` and the project's own tests under `tests/`. A test added under `tests/` in a target
> is collected and run by `make test`; a failing one makes it fail.

**Tests.** `tests/kit_dev/test_init.py` (sample project test collected and run; failing sample fails `make test`) and
`tests/kit_dev/test_kit_manifest.py` (Makefile target and both `testpaths`), marker `REQ-009 AC2`.

**Status.** Applied to `docs/specs/0001-agk-init.md` on maintainers' instruction, in the same PR as this file.
Recorded in ADR-0005.

# Run report: day 3 (PR #6, agk init implementation)

Date: 2026-10-14 (from `date -u`). Implements SPEC-0001 (Approved). Tests first: the tests in `tests/kit_dev/` and the
rule 22 test were written before `init.py`; the first run was red (init missing), then green.

## Decisions taken

- Manifest generated from the tracked files once and kept explicit (`kit/manifest.json`); `test_kit_manifest.py`
  fails when a law file is missing from it (SPEC rules 6-9).
- Kit version `0.1.0` (first installable version; the spec leaves the value open).
- Project name for `pyproject.toml` is the slug of the target directory name (lowercase, non-alphanumerics to `-`).
- Refusal also covers a symlinked path and a non-directory TARGET; both exit 1 and write nothing (rules 2-3).
- Rule 22 already held in the checks (they only look up defined requirements); a test now pins it.
- `ruff` target for installed files is the kit's own config, copied into the installed `pyproject.toml`.

## Spec deviations

- None. No `docs/runs/proposed-spec-amendments-1.md` was needed.

## Questions

- Q-K1-13: the installed `.claude/settings.json` is verbatim, so it also asks before editing `kit/` and
  `tests/kit_dev/`, which do not exist in a target (harmless). Alternative: render settings from a template. Accept?
- Q-K1-14: `make governance` in a target needs a base branch; with no `main`/`origin/main` the diff checks skip
  with a notice outside CI. Accept for K1?

## Verified

See the PR body.

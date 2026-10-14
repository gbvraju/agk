# Proposed spec amendments 3

Date: 2026-10-14 (from `date -u`). Found while implementing SPEC-0002 rules 1-4, 7, 9, 11, 13-18 (ADR-0008).
Approved specs change only through a proposal like this one (principle 6). Nothing here is applied to a spec;
maintainers decide.

## SPEC-0002 (`docs/specs/0002-agk-adopt.md`)

1. **Rule 3, the stamp is read as text.** To honour rule 17, adopt also scans `agk.toml` for a `mode` line and
   `pyproject.toml` for a `[tool.agk]` header as plain text, and reads its own `agk.toml` (parsed as TOML) to reuse
   a stamp. No other target file is parsed.
2. **Rule 4, block files.** An absent `.gitignore` is created containing the marked block only; the other block
   files are created whole when absent. An appended block keeps the existing bytes as a prefix; a file without a final
   newline gets one newline before the block.
3. **Rule 9, detection details.** `test_dirs` is the topmost directories holding matching files; a matching file at
   the repository root makes it `["."]`; hidden directories, `node_modules`, `__pycache__`, `venv`, `env`, `build`,
   `dist`, `site-packages`, `tox`, `tests/kit` and `scripts/agk` are skipped; with no match the defaults are
   `["tests"]` and `["test_*.py"]`. A second run reuses the stamped `test_dirs` and `test_patterns`. Markers in
   `tests/kit` are excluded from the search in adopt mode unless a listed directory is inside it.
4. **Rule 11, CODEOWNERS block check (shared kit).** `reviewers.py --check-codeowners` compares only the marked block
   of a CODEOWNERS that has one, so a project's own lines are free; a broken or duplicated block fails.
5. **Rule 13, existing protected files.** The ADR lists the project's files in a protected class that adopt does not
   itself write (so the list is the same on a second run).
6. **Rule 16, dry-run lines.** `--dry-run` also prints `unchanged` and `append`; the real run prints the same lines
   before writing.
7. **Rule 5, template variables for adopt.** Adopt templates may use `{{test_dirs}}`, `{{test_patterns}}` and
   `{{existing_protected}}` in addition to the init variables.
8. **Kit version.** Installed content changed (`common.py`, `reviewers.py`, the checks that find markers, new
   template files), so the kit version is `0.4.0`.

## Status

Proposed. Not applied.

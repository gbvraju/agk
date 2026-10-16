# ADR-0022: shared helpers for the facts engine (behaviour-preserving, kit 0.11.1)

- Status: Accepted
- Date: 2026-10-16
- Deciders: maintainers
- Related: ADR-0021, ADR-0015
- Requirements: REQ-018

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`

## Context

SPEC-0009 (Approved) builds `scripts/agk/facts.py` and requires that it imports the code that already parses a
requirement, an acceptance line, a marker and a register line instead of copying a pattern (rule 16). Rule 17 lists
three behaviour-preserving changes to existing scripts that make the imports possible, and says that if together they
exceed about 150 changed lines they land first, in their own pull request. Measured here: `git diff --stat` of the code
alone is 119 insertions and 22 deletions, and the tests that show the output is unchanged add about 250 lines more, so
this is that first pull request. `facts.py` follows in the next one.

## Decision

1. **`common.parse_requirements`** also returns `title` (the text after the em dash of the header, else `None`) and
   `acceptance` (the raw text of the first `- Acceptance:` line, else `None`). Callers that read `id`, `status`,
   `status_count` and `line` are unchanged.
2. **`common.parse_acceptance(text)`** implements the grammar of SPEC-0009 rule 8 and returns `(ACn, text)` pairs;
   **`common.find_ac_markers(root, dirs, patterns, exclude)`** implements rule 9 and returns `{req, ac, file, line}`
   objects. `common.find_markers` keeps its signature and its result; both functions share one file walk,
   `common._marker_files`, which differs only by the directory names it skips (`find_markers` skips `__pycache__` as
   before; the new function also skips `.git`, `node_modules`, `vendor`, `target` and `.venv`, Q-K4-6).
3. **`drift_audit.register_lines(text)`** is extracted from `d4_register` (the loop that splits a register line into its
   fields) and returns the parsed lines; `d4_register` calls it and reports the same findings.
4. **Proof that nothing changed.** `tests/kit/test_common_refactors.py` holds the code of the three functions as it was
   (`legacy_*`) and shows equal results on this repository and on fixtures, then tests the new helpers (the grammar,
   runs of requirement ids, a non-Python tree, the skipped directories, the adopt-mode exclusion). The existing test
   suites pass unchanged. The output of `drift_audit.py` (two dates, with and without open audit issues, and
   `--print-action`), `check_requirements.py` and `traceability.py` on this repository is byte-identical before and
   after (recorded in the pull request body).
5. **Kit 0.11.1** (a patch: installed content changed with no change of behaviour, SPEC-0008 rule 25). The plugin
   version is bumped with it (`tests/kit_dev/test_distribution.py`). `kit/hashes.json` is regenerated with
   `python3 scripts/agk/kit_hashes.py --write`; the manifest gains the one new installed test.

## Consequences

- `facts.py` (the next pull request) can import every parser it needs.
- Installed repositories receive three small functions and one test file at their next `agk upgrade`.

## Residual

- 2026-10-16: the new marker search walks the tree with `rglob` and skips directories afterwards; a repository with a
  very large `node_modules` under a listed test directory is slow to read. A pruned walk would change the shared file
  walk and is not done here (due 2026-12-31).

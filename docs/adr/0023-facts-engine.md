# ADR-0023: the facts engine (SPEC-0009), kit 0.12.0

- Status: Accepted
- Date: 2026-10-16
- Deciders: maintainers
- Related: ADR-0021, ADR-0022
- Requirements: REQ-018, REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`

## Context

SPEC-0009 (Approved) defines one document, produced by `scripts/agk/facts.py`, that every K4 feature reads: the report, the
inbox, the proof checks and the playbook take their numbers and statuses from it and from nothing else (ADR-0021 decision 2,
exit criterion e). ADR-0022 (Accepted) landed the shared parsers it imports. This is the second pull request of the day-11
brief.

## Decision

1. **`scripts/agk/facts.py`** (installed, verbatim) builds the document of SPEC-0009 rules 1 to 15: fifteen fixed top-level
   keys, schema `1`, keys sorted, two-space indent, `"unknown"` for a value that could not be read, exit 0 whatever the document
   contains, exit 1 for a refusal that names the path class `root`, exit 2 for usage. It reads GitHub only through
   `metrics.Gh` (`gh api --method GET`) or `metrics.ApiDir` (recorded files); it writes nothing and holds no credential.
2. **It imports and does not copy** (rule 16): `common.parse_requirements`, `parse_acceptance`, `find_ac_markers`,
   `load_config`; `check_specs.status_of`; `check_adrs.status_of`, `FIELD_RE`, `FILE_RE`, `TITLE_RE`;
   `drift_audit.residual_bullets`, `DUE`, `parse_date`, `register_lines`, `audit`, `docs`, `read`; `metrics.verdicts`,
   `Gh`, `ApiDir`. A test reads the script and asserts the list. The `drift` section calls `drift_audit.audit` and counts its
   findings; it never reads an issue body.
3. **`kit/facts-schema.json`** is a hand-written JSON Schema (`type`, `required`, `properties`, `additionalProperties`, `items`,
   `enum`, `const`, `pattern`, `oneOf`), kit-only, with no generator. `tests/kit_dev/jsonschema_lite.py` implements exactly
   those keywords and raises on any other. `tests/kit_dev/test_facts_wiring.py` validates every golden and the document for
   this repository at `HEAD`.
4. **Tests and fixtures** (installed): `tests/kit/test_facts.py` and `tests/kit/fixtures/facts/<case>/` for eleven cases
   (`ok`, `empty`, `offline`, `unstructured-acceptance`, `duplicate-ac`, `multi-req-marker`, `go-style`, `residual-forms`,
   `question-forms`, `pr-states`, `dirty`) plus `drift-counts` built in the test. Each case runs twice (byte-identical) and
   equals its golden; each source is removed in turn and exactly its sections turn `"unknown"`. Goldens are rewritten only by
   `python3 tests/kit/test_facts.py --write-goldens`, run by a person.
5. **`common.DEFAULT_CONFIG` gains `inbox_hours` (48)** so that the document carries SPEC-0011's setting with its default
   when `agk.toml` lacks the key (SPEC-0009 rule 7). No other consumer reads the key.
6. **Kit 0.12.0** (a minor: a new installed script, test and fixtures); the plugin version follows;
   `kit/hashes.json` is regenerated with `kit_hashes.py --write`.
7. **Questions** `Q-K4-110` to `Q-K4-120`, below, were readings the Approved text did not settle; the maintainers ruled every one
   accepted on 2026-10-16.
8. **Amendments 16, applied by this ADR** on the maintainers' acceptance of the proposal: `docs/specs/0009-facts.md` rule 14 loses the
   sentence "the window is a field `weeks`" (option (a)); rule 5 and rule 7 gain the sentences of items 3 and 2; rule 17 gains (d). The
   spec is not in a protected class (`config/protected-paths.txt`), so no class is added; `check_specs` is satisfied by the amendments
   file that names the spec in the same change set.

## Consequences

- Installed repositories receive `facts.py`, its test and its fixtures at their next `agk upgrade`.
- SPEC-0010, SPEC-0011 and SPEC-0013 code reads this document; none of them reads a repository file directly.
- The document for a repository with a large pull request history costs one `files` and one `comments` call per pull request in
  the window (SPEC-0009 residual).

## Questions

| Q | Question | Reading taken (ruled: accepted) |
| --- | --- | --- |
| Q-K4-110 ruled | `inbox_hours` has no source: `load_config` returns only the keys of `DEFAULT_CONFIG`. | the key is added to `DEFAULT_CONFIG` with default 48 (decision 5) |
| Q-K4-111 ruled | Rule 14 says "the window is a field `weeks`", and rule 3 fixes the top-level keys and makes `pull_requests` an array of pull requests; there is no place for it. | `--weeks` selects the window and no field records it; the window is the ISO week of `today` and the `weeks - 1` before it; amendment 16 |
| Q-K4-112 ruled | With no `agk.toml` and no `[tool.agk]`, `load_config` silently uses defaults, which rule 5 forbids. | `config`, `markers` and `drift` are `"unknown"` (the defaults are not the repository's settings) |
| Q-K4-113 ruled | A missing single file: `docs/requirements.md`, `docs/runs/residuals.md`, `docs/runs/decisions-log.md`. | `requirements`, `residuals` and `questions` are `"unknown"`; `specs[].open_questions` is `"unknown"` without the log; a missing directory (`docs/specs`, `docs/adr`) is `[]` |
| Q-K4-114 ruled | `open_questions` and `open_in` use "the `## Open` section of a notes file". | the heading is exactly `## Open` in a file `docs/runs/spec-NNNN-notes.md`; `## Open questions` does not count until amendment 14 item 2 is applied |
| Q-K4-115 ruled | A verdict entry of kind `fix` or `rejected` has no sha; `at` has no source but the comment. | `sha` is `null` for those kinds; `at` is the comment's `created_at` |
| Q-K4-116 ruled | `base` of a pull request: a branch name or a commit. | the base branch name (`head` is the SHA) |
| Q-K4-117 ruled | The pull request set and the API names. | open pull requests, plus closed ones whose `closed_at` is on or after the Monday `weeks - 1` weeks before the Monday of `today`'s week and created on or before `today`; the list items carry the body, so no per-pull-request detail call; recorded files are `pulls-open`, `pulls`, `files-N`, `comments-N`, `runs-SHA`, `jobs-RUNID`, `issues-LABEL`; the paging of `metrics.Gh` is used through its `pages` method because `Gh.get` pages only the names `metrics.py` uses |
| Q-K4-118 ruled | `residuals` from the register: the `source` of a line. | the register's own path (`docs/runs/residuals.md`); the `text` is the line's text field (the origin file and date of the bullet are not kept) |
| Q-K4-119 ruled | `criteria_form` when two criteria share a number. | `"structured"` with `criteria: "unknown"` |
| Q-K4-120 ruled | `repo` from `origin`. | parsed in `facts.py` (`metrics.origin_repo` reads the current directory and an environment variable, not ROOT) |

## Residual

- 2026-10-16: the marker search shares the `rglob`-then-skip walk of ADR-0022; a repository with a very large dependency
  directory under a listed test directory is slow to read (due 2026-12-31).
- 2026-10-16: the `proof` field reads the step names `outcome: <word>` of the `proof` job (SPEC-0010 rule 17); the workflow does
  not exist yet, so every pull request reads `"unknown"` until SPEC-0010 is built, and `(verify)` that GitHub returns step names
  and conclusions for every step is proved on this repository when it is (due 2026-11-30).
- 2026-10-16: `"unknown"` marks a missing source but not an unreadable one inside a section (a file that is not UTF-8 is skipped
  where the existing scripts skip it) (due 2026-12-31).

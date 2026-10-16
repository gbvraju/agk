# SPEC-0009: facts (one document that every K4 feature reads)

- Status: Approved
- Owner: maintainers
- Requirements: REQ-018 (AC2, the foundation of "no typed numbers"); REQ-015, REQ-016, REQ-017 (they read this document)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
This spec is the first of the five K4 specs of ADR-0021 and serves exit criterion e (no typed numbers). The points
`Q-K4-1` to `Q-K4-19` were ruled by the maintainers on 2026-10-16 (`docs/runs/spec-0009-notes.md`). Facts about GitHub not reconfirmed are marked
`(verify)`. The repository facts quoted here were read on 2026-10-16 (`docs/runs/spec-0009-notes.md`).

## Rules

### What it is

1. **Command.** `python3 scripts/agk/facts.py [--today YYYY-MM-DD] [--repo OWNER/REPO] [--api-dir DIR] [--weeks N] [ROOT]`.
   Standard library only. ROOT is the work tree to read (default `.`; it must be a git work tree with at least one commit).
   `--today` defaults to `date -u` (the current UTC date). The script is vendored into every target (listed in
   `kit/manifest.json` `verbatim`) and runs without the plugin (SPEC-0005 rule 2). The document goes to stdout; nothing is
   written to a file.
2. **Read-only, no credential.** The script writes no file, makes no commit, runs no `git` command that changes anything
   (it uses `rev-parse`, `ls-files`, `status --porcelain` and `show`, and the read-only commands of the drift audit's finding
   functions, rule 15), and reads GitHub only with `gh api --method GET`
   (the Gh and ApiDir readers of `metrics.py`, rule 16). It never reads, prints or stores a token: `gh` holds the credential.
   It makes no other network call.
3. **One document, a fixed set of keys.** The top-level keys are exactly `schema`, `commit`, `dirty`, `today`, `repo`,
   `config`, `requirements`, `markers`, `specs`, `adrs`, `residuals`, `questions`, `pull_requests`, `issues` and `drift`. `schema` is
   the integer `1`. `commit` is the SHA of `HEAD` in ROOT. `dirty` is `true`, `false` or `"unknown"` (a tracked file differs from
   `HEAD`, from `git status --porcelain`). `today` is the date of rule 1. `repo` is `OWNER/REPO` from `--repo` or from the URL of
   `origin`, else `"unknown"`. Every other key is a section (rules 7 to 15). A K4 feature reads this document and nothing
   else (ADR-0021 decision 2); it reads no key outside this list.
4. **Determinism.** The same `HEAD` with a clean work tree, the same `--today`, the same `--weeks` and the same API
   fixtures give byte-identical JSON: keys sorted, arrays sorted by the key each section names, two-space indent, one
   trailing newline, ASCII-safe escapes, no timestamp other than `today`, no path outside ROOT, no absolute path. A
   document with `dirty: true` is still produced, and its `commit` no longer reproduces it; consumers print the flag (rule 24).
5. **Unknown, never a default.** A value that could not be read is the string `"unknown"`, at the smallest level that
   fits: one field, or the whole section when the section's source is unavailable (offline mode, a failed `gh` call, a missing
   file). An empty section that was read is `[]`. A number is never filled with `0` when the source is missing. An
   `"unknown"` is not an error: the exit status is 0 (rule 6). With no `agk.toml` and no `[tool.agk]` table in `pyproject.toml`,
   `config`, `markers` and `drift` are `"unknown"`: the defaults of `common.load_config` are not the repository's settings.
6. **Exit codes and refusals.** 0 when the document was written, whatever it contains. 1 for a refusal, before any output:
   ROOT is not a directory, is not a git work tree, or has no commit (messages name the path class, never a value). 2 usage.
   3 I/O error on a file that is required to exist (`.git` unreadable). `facts.py` never fails because a section is `"unknown"`.

### The sections

7. **`config`.** The values the K4 features need from `agk.toml` (read with `common.load_config`): `default_branch`,
   `test_dirs`, `test_patterns`, `inbox_hours` (SPEC-0011; default 48 when the key is absent) and `project_tests_declared`
   (`true` when the `project_tests` key is non-empty; the command itself is not copied). No other key is copied. `inbox_hours` is a
   key of `common.DEFAULT_CONFIG` (value 48), so that `load_config` returns it (rule 17 (d)).
8. **`requirements`.** One object per `### REQ-nnn` section of `docs/requirements.md`, sorted by id: `id`, `title` (the text
   after the em dash), `status` (`planned`, `in-progress` or `done`, else `"unknown"`), `line`, and `criteria`: an array of
   `{"id": "AC1", "text": "..."}` in file order. **Acceptance grammar.** The `- Acceptance:` line is split at each
   occurrence of `AC<digits>` that starts the line text or follows `; `, and a criterion's text runs to the next such
   marker; trailing `;` and spaces are removed. A requirement with no `- Acceptance:` line, or whose line has no `ACn`
   token, has `criteria: []` and `criteria_form: "unstructured"` (otherwise `"structured"`); the facts document never invents a
   criterion. Two `ACn` with the same number in one requirement make the section `criteria: "unknown"` and the repository a
   finding for SPEC-0010.
9. **`markers`.** Every marker found in the test files, as an object `{"req", "ac", "file", "line"}` sorted by file, line,
   req, ac. The files are those matching `test_patterns` under `test_dirs` of `agk.toml` (the rule of `common.find_markers`,
   including its `tests/kit` exclusion in adopt mode), read as text in any language. **Marker grammar.** A marker is a
   `REQ-nnn` token, alone (`ac: null`) or in a run of one or more `REQ-nnn` tokens separated by spaces, commas or `/` that is
   immediately followed by a space and `AC<digits>` (`REQ-009 AC2`, `REQ-001 REQ-002 AC2`, `REQ-001/REQ-002 AC2`); the `ACn`
   then attaches to every `REQ` of the run. One `ACn` per run: `AC1 AC2` is two runs only when each is preceded by its own
   `REQ`. A marker inside any comment or string counts alike; whether the marked test is meaningful is not judged (SPEC-0010
   rule 14). Directories named `.git`, `node_modules`, `vendor`, `target`, `__pycache__` and `.venv` are skipped (Q-K4-6).
10. **`specs`.** One object per `docs/specs/NNNN-*.md` (not `TEMPLATE.md`), sorted by id: `id` (`SPEC-NNNN`), `title`,
    `status` (`Draft` or `Approved`, from `check_specs.status_of`), `requirements` (the sorted `REQ-nnn` tokens of its
    `- Requirements:` line), `notes` (the path of `docs/runs/spec-NNNN-notes.md` when it exists, else `null`), and `open_questions`
    (the `Q-` ids named in the notes file under `## Open` that the decisions log does not rule, rule 13).
11. **`adrs`.** One object per `docs/adr/NNNN-*.md` (not `TEMPLATE.md`), sorted by id: `id` (`ADR-NNNN`), `title`, `status` (from
    `check_adrs.status_of`; one of its four), `date`, `amends` (the list from the `- Amends:` field, `[]` if none),
    `requirements`, and `protected_classes` (the backticked entries of its `Protected classes:` line, `[]` if none).
12. **`residuals`.** One object per residual line, from three sources, sorted by source then position: the `## Residual` bullets
    of specs and ADRs (`drift_audit.residual_bullets`), and the lines of `docs/runs/residuals.md` (`## Open`: `state: "open"`;
    the table under `## Closed`: `state: "closed"`). Fields: `source` (file path), `text`, `due` (`YYYY-MM-DD`, parsed with
    `drift_audit.DUE` and `drift_audit.parse_date`; `null` when the bullet carries no date; `"unknown"` when the date is
    malformed) and `state` (`open` for a bullet of a spec or ADR; `closed` only for the register's closed table). Overdue-ness is
    not a field: a consumer compares `due` with `today`.
13. **`questions`.** One object per `Q-<family>-<n>` id (pattern `Q-[A-Z0-9]+-[0-9]+`) found in any `.md` file under `docs/`,
    sorted by id: `id`, `files` (sorted paths), `ruled` (`true` when a row of `docs/runs/decisions-log.md` contains the text
    `<id> ruled`; from 2026-10-16 every ruling row of the log names its id and says `ruled`), `named_in_log` (a row contains the id in any form), and `open_in` (the sorted paths among `files` that are
    a notes file of a `Draft` spec, a `Proposed` ADR or the `## Open` section of a notes file). A question is *waiting* when
    `open_in` is non-empty and `ruled` is `false` (SPEC-0011 rule 4); the facts script states the three booleans and no more.
14. **`pull_requests`.** Read from the GitHub REST API (`gh api --method GET`, paged by hand as `metrics.Gh`), or from the
    recorded files of `--api-dir` (names as in `metrics.ApiDir`). The set is every pull request that is open, plus every
    pull request created or closed in the last `--weeks` ISO weeks (default 8). Each object, sorted
    by number: `number`, `state` (`open`, `merged` or `closed`), `created_at`, `closed_at`, `merged_at`, `head` (SHA), `base`,
    `title`, `files` (sorted paths), `proof` (`proven`, `not-proven`, `skipped` or `unknown`: the outcome of the workflow run named
    `proof` for the head SHA, read from the step conclusions of its job as SPEC-0010 rule 17 defines; `"unknown"` when there is no such
    run or the API could not be read), `verdicts` (the list `[{"kind": "cleared"|"fix"|"rejected", "sha", "at"}]` in time order,
    from the first line of each comment by the rule `metrics.VERDICT`/`metrics.verdicts`), and `behaviour` (`"unchanged"` when a
    line of the body, outside fenced code, is exactly `Behaviour: unchanged`; `null` when the body has no `Behaviour:` line;
    `"unknown"` when the body could not be read). With no GitHub source (offline, no `gh`, unauthenticated) the section is
    `"unknown"`. The body is read for the `Behaviour:` line and for nothing else (ADR-0021 criterion e).
15. **`issues` and `drift`.** *`issues`:* the open and closed issues labelled `agk-metrics`, `agk-drift-audit` or `agk-product-report`, as
    `{"number", "title", "label", "state"}` sorted by number; nothing from their bodies. `"unknown"` without a GitHub source. *`drift`:*
    the findings of the drift audit (SPEC-0004) at the same commit and `today`, counted and not described:
    `{"counts": {"<kind>": n, ...}, "total": n}` with one count for every finding kind the audit defines (`drift_audit.CODES`; `D1` to
    `D7` today), each present and `0` for a kind with no finding, and `total` the number of findings of all those kinds. It is computed by calling `drift_audit.audit(root, today, branch, open_issues)` (the audit's own finding functions, which
    read the repository and write nothing), where `branch` is `config.default_branch` and `open_issues` is the list of numbers of the
    open issues labelled `agk-drift-audit` taken from `issues`, so that D6 (duplicate audit issues) sees them. The body of the drift
    issue is never read; the issue's number stays in `issues` for linking. When `issues` is `"unknown"`, `D6` and `total` are
    `"unknown"` and D1 to D5 are still counted; when the default branch cannot be resolved the whole section is `"unknown"`.

### Reuse, never re-parse

16. **What `facts.py` imports.** Wherever the repository already parses a thing, `facts.py` imports that code; it does not
    copy a pattern.

    | Thing | Imported from |
    | --- | --- |
    | requirement sections, status, line | `common.parse_requirements` (rule 17 adds `title` and `acceptance`) |
    | acceptance criteria | `common.parse_acceptance` (new, rule 17) |
    | marker search and its adopt-mode exclusion | `common.find_markers` and `common.load_config`; `common.find_ac_markers` (new, rule 17) |
    | spec status | `check_specs.status_of` |
    | ADR status, fields, title and number patterns | `check_adrs.status_of`, `check_adrs.FIELD_RE`, `check_adrs.TITLE_RE`, `check_adrs.FILE_RE` |
    | residual bullets, due date, date parse, register lines | `drift_audit.residual_bullets`, `drift_audit.DUE`, `drift_audit.parse_date`; `drift_audit.register_lines` (new, rule 17) |
    | drift counts | `drift_audit.audit` and the finding functions it calls (rule 15) |
    | verdict comments | `metrics.VERDICT`, `metrics.verdicts` |
    | `gh api` GET and recorded files | `metrics.Gh`, `metrics.ApiDir` |

17. **Behaviour-preserving changes to existing scripts.** (a) `common.parse_requirements` also returns `title` and
    `acceptance` (the raw text of the line); callers that read `id`, `status`, `status_count` and `line` are unchanged. (b)
    `common.parse_acceptance(text)` implements the grammar of rule 8; `common.find_ac_markers(root, dirs, patterns, exclude)`
    implements rule 9 and is built beside `find_markers`, which keeps its signature and result. (c) `drift_audit.register_lines(text)`
    is extracted from `d4_register` (the loop that splits a register line into its four fields) and returns the parsed lines;
    `d4_register` calls it. (d) `common.DEFAULT_CONFIG` gains `inbox_hours` (48), which `load_config` returns to every caller; no existing
    caller reads it, and the test of the default configuration lists it. For each of (a) to (c) a test shows that the output of the existing scripts is byte-identical before and
    after on the repository and on the existing fixtures. If the three changes together exceed about 150 changed lines, the implementation splits them into a first pull request that lands
    before the one that adds `facts.py`. Where an import is impossible, the reason is stated here and a residual records the
    convergence (none is known today).
18. **What it does not do.** It counts nothing the existing scripts count (the `drift` counts of rule 15 are the audit's own findings, called and not recounted): `tests_before`, `tests_after` and every metrics
    field stay in `metrics.py` (ADR-0021 residual). It judges nothing: no field says a requirement is well tested, only that a
    marker exists. It runs no test, no model and no check.

### Schema and fixtures

19. **The schema file.** `kit/facts-schema.json` is a hand-written JSON Schema (the draft-2020-12 keywords `type`, `required`,
    `properties`, `additionalProperties`, `items`, `enum`, `const`, `pattern`, `oneOf`), **a committed file, not a generated
    one**: unlike `kit/hashes.json` it has no generator and no regeneration test, and it is changed by hand with the document
    it describes. It is kit-only (not installed). `schema` in the document equals `const` in the schema file; any change to a
    key or a meaning raises `schema` and is an amendment of this spec. The test validator is a small stdlib function
    (`tests/kit_dev/`) that implements exactly the keywords above; it fails on a keyword it does not implement.
20. **Fixtures.** `tests/kit/fixtures/facts/<case>/` holds `tree/` (the repository files), `api/` (recorded API responses, owner
    and ids changed, no secret; for `proof` the run list and the job of the head SHA, `runs-<sha>.json` and `jobs-<id>.json`), `case.json` (`today`, `weeks`, and the arguments) and `facts.json` (the golden document). The
    cases: `ok` (one of everything), `empty` (a repository with the minimum files: every section `[]`), `offline` (no API: the
    API sections `"unknown"`), `unstructured-acceptance`, `duplicate-ac`, `multi-req-marker` (`REQ-001 REQ-002 AC2` and the
    slash form), `go-style` (a non-Python tree with `*_test.go` and `//` comments), `residual-forms` (dated, undated, malformed
    date, register open and closed), `question-forms` (ruled, named only, in a Draft notes file, in an Approved spec's notes),
    `pr-states` (open, merged, closed; verdicts in time order; `Behaviour: unchanged` in a code fence ignored; each of the four `proof`
    outcomes, and a run with two succeeded outcome steps, which is `"unknown"`), and
    `dirty` (a modified tracked file), and `drift-counts` (a repository built as in the drift-audit fixtures of SPEC-0004,
    `tests/kit/drift_fixtures.py`, with known counts for every kind the audit defines, once with and once without the list of `agk-drift-audit` issues). The goldens are changed only by a person running the documented command in the test
    file; no test rewrites a golden.

### Installed files, proof

21. **What is built.** `scripts/agk/facts.py` (verbatim, installed), the changes of rule 17, `tests/kit/test_facts.py` and the
    fixtures (installed, run by `agk-test`), `kit/facts-schema.json` and `tests/kit_dev/test_facts_wiring.py` (kit-only).
    The classes touched are `scripts/agk/`, `tests/kit/`, `kit/` and `tests/kit_dev/`; the implementation PR carries an ADR that
    names each. The kit version is bumped (SPEC-0008 rule 25).
22. **Determinism and unknown are tested.** A test runs each fixture case twice and compares bytes, then compares with the
    golden. A test removes each source in turn (the `gh` executable from `PATH`, `docs/runs/residuals.md`, the decisions log,
    `agk.toml`) and asserts that exactly the sections that depend on it are `"unknown"` and that no other byte changes.
23. **This repository, and the pilot.** A kit-only test builds the document for this repository at `HEAD` and validates it
    against `kit/facts-schema.json`. The document for the pilot repository (a Go module; `test_patterns` `["*_test.go"]`,
    `test_dirs` `["."]`) is produced by the same script with no change, and the `go-style` fixture is its stand-in in the
    kit's tests (SPEC-0010 rule 20 describes the pilot run).
24. **A consumer prints what is not certain.** A consumer that prints a number from this document prints `unknown` as
    `unknown`, and prints a notice when `dirty` is not `false` (SPEC-0011 rule 12).
25. **Order.** This spec is built first (ADR-0021 decision 7: facts engine by 2026-11-09). Metrics and the drift audit are not
    rewritten onto this document in K4 (ADR-0021 residual, due 2027-01-31).

## Tests

- Rules 1 to 6, 22: `tests/kit/test_facts.py`, marker `REQ-018 AC2`.
- Rules 7 to 15 over the fixture cases of rule 20 (including the `drift` counts): the same file, marker `REQ-018 AC2`.
- Rules 16, 17: the same file (the import list is asserted by reading `facts.py`) and the before-and-after tests of the existing
  scripts, marker `REQ-018 AC2`.
- Rules 19, 23: `tests/kit_dev/test_facts_wiring.py`, marker `REQ-018 AC2`.
- Rule 9 (markers of any language), rule 20 `go-style`: the same file, marker `REQ-016 AC1`.
- Rule 8 (`criteria` as read) feeds `REQ-015 AC1`; its own test is in SPEC-0010.

## Proof

This spec serves ADR-0021 exit criterion e: *a test shows every number and every status in the report is computed from the
facts document, and the report names the facts commit.* Facts provides the document and its `commit` and `dirty` fields. The
proof that the report uses only the document is in SPEC-0011 rule 13 (the renderer takes `--facts FILE` and reads nothing
else; a test greps it for any file or network read). Facts itself is proved by the determinism, golden, `unknown` and schema
tests above, and by the schema validation of this repository's own document. A live run is recorded in `docs/runs/` when the
engine is built: the document for this repository at `HEAD`, run twice, byte-identical, with its size and its `unknown`
sections.

## Residual

- 2026-10-16: the `drift` section calls the drift audit's finding functions a second time at facts time; the audit and the facts both
  read the repository for D1 to D5 until the audit moves onto the facts (due 2027-01-31).
- 2026-10-16: metrics and the drift audit read the repository with their own parsers; moving them onto this document is a later
  change by amendment (due 2027-01-31).
- 2026-10-16: the facts script reads every pull request of an 8-week window page by page; a repository with many pull
  requests per week makes it slow, and a cache is not designed (due 2026-12-31).
- 2026-10-16: marker search treats a marker inside a comment or a string alike, so a marker in a skipped or dead test is a
  marker; the red-then-green check (SPEC-0010) is the answer for new tests, and nothing answers it for old ones (due 2027-01-31).
- 2026-10-16: `agk.toml` has one `test_patterns` list for all languages; a repository with tests in two languages lists both
  patterns (due 2026-11-30).

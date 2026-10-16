# Notes on SPEC-0009 (facts)

Date: 2026-10-16 (from `date -u`). Overnight brief 3, item A. The spec is written **Draft**; nothing is implemented and no
protected path is changed by this pull request. It is the first of the five K4 specs of ADR-0021 (decision 2) and serves exit
criterion e. Every question below is raised, not ruled: for each the spec takes the conservative reading and says so.

## What exists today (read on 2026-10-16, on `main` at 94a807d)

- **Requirements.** `docs/requirements.md` has 20 requirements: 2 `done` (REQ-001, REQ-003), 1 `in-progress` (REQ-002), 17
  `planned`. All 20 `- Acceptance:` lines have the form `AC1 …; AC2 …` (every `ACn` is at the start of the text or after `; `).
  `common.parse_requirements` returns `id`, `status`, `status_count` and `line` only; it does not return the title or the
  acceptance text.
- **Markers.** `common.find_markers` records which files carry a `REQ-nnn` token, per requirement, with no line numbers and no
  `ACn`. Under `tests/` there are 543 `REQ-nnn ACn` markers in 34 files: 542 name one requirement and 1 names two
  (`REQ-001 REQ-002 AC2`). The kit's own tests already use the marker form the spec describes.
- **Specs and ADRs.** `check_specs.status_of` and `check_adrs.status_of` read the `- Status:` line. `check_adrs` holds the field,
  title and file-name patterns (`FIELD_RE`, `TITLE_RE`, `FILE_RE`). 21 ADRs and 8 specs exist. Spec 0009 to 0013 are the K4 specs.
- **Residuals.** `drift_audit.residual_bullets` reads the `## Residual` bullets of specs and ADRs (85 bullets today);
  `docs/runs/residuals.md` has 26 open lines. The register line is split inside `drift_audit.d4_register`, not in a function
  of its own.
- **Questions.** 115 distinct `Q-<family>-<n>` ids appear under `docs/` (families Q-K0, Q-K1, Q-K2, Q-K3, Q-ON, Q-SR2, Q-SR3,
  Q-SR4, Q-D10). 90 are named in `docs/runs/decisions-log.md` in some form; only **33** are in a row that says `<id> ruled`. The
  other rulings are recorded in the `## Rulings` tables of the notes files, not in the log.
- **Pull requests.** `metrics.Gh` and `metrics.ApiDir` already read the API (GET only) and recorded files; `metrics.verdicts`
  and `metrics.VERDICT` read `Verdict:` first lines; `metrics.py` has the paging and the `--api-dir` file names. `Behaviour:`
  is not read anywhere today.
- **Config.** `common.load_config` reads `agk.toml` with defaults for `default_branch`, `test_dirs`, `test_patterns`, `project_tests`.
  `inbox_hours` does not exist yet.

## Decisions taken in the draft (each is a numbered rule)

- One script, one JSON document, one fixed key list, stdout only (rules 1 to 3). A K4 feature reads the document and nothing
  else, which is what makes criterion e testable: if a number is wrong, it is wrong in one place.
- Determinism by construction: sorted keys and arrays, no timestamp but `today` (rule 4). The honest limit is a dirty work
  tree, so the document carries `dirty` (Q-K4-2) instead of promising what it cannot.
- `"unknown"` at the smallest level, never a default and never an error (rules 5, 6). This is the same discipline as the doctor's
  `cannot-check` and metrics' `unknown`.
- Import, never re-parse (rules 16, 17): the table names the function behind each section; the three missing functions are
  extracted from or added beside existing code with a behaviour-preserving test.
- The schema is a committed hand-written file, not generated (rule 19), kit-only. It is the contract that SPEC-0011 and the
  later specs rely on.
- Metrics and the drift audit are not touched in K4 (ADR-0021 decision 2); a residual records the later move.

## Options compared

| Question | Option taken | Not taken, and why |
| --- | --- | --- |
| How do features get repository data | one facts document | each feature parses for itself: that is the status quo, with three parsers of the same markdown already (`check_requirements`, `drift_audit`, `metrics`) |
| Format | JSON on stdout | a SQLite file (a binary artefact, not diffable); a committed file (a second generated file, principle 5; `kit/hashes.json` was already one exception) |
| Where the schema lives | a hand-written `kit/facts-schema.json`, kit-only | generating it from the script (the schema would then prove nothing); installing it (targets would need a validator they do not have) |
| Pull request window | open PRs plus the last 8 ISO weeks | all history (slow, and the report needs one week); one week only (the inbox needs open PRs older than a week) |
| Marker grammar | a run of `REQ` tokens before `ACn` attaches the `AC` to each | one marker per line only (breaks the existing `REQ-001 REQ-002 AC2`); a new syntax (a rewrite of 543 markers) |
| Acceptance split | at `AC<digits>` at the start or after `; ` | also after `. ` (not needed by any of the 20 lines today and would split a sentence that names an `AC` in prose) |
| Schema validator | a small stdlib function in the test | the `jsonschema` package (a new dependency, rule 5 of CLAUDE.md allows none in checks) |

## Open questions (none is ruled; the spec takes the conservative reading)

| Q | Question | Reading taken in the spec |
| --- | --- | --- |
| Q-K4-1 | The brief says the facts record "`Verdict:` and `Behaviour:` first-line comments". ADR-0021 and SPEC-0010 put `Behaviour: unchanged` in the **PR body**. Which? | `Behaviour:` is read from the PR body (a line, outside code fences); `Verdict:` from comments, as metrics does (rule 14) |
| Q-K4-2 | The brief does not list `dirty`. A document made from a modified work tree cannot be reproduced from its `commit`. | add `dirty` (`true`/`false`/`"unknown"`) and make consumers print a notice (rules 3, 4, 24) |
| Q-K4-3 | `config` is not in the brief's list, but SPEC-0011 needs `inbox_hours` and SPEC-0010 needs to know whether `project_tests` is declared. | a `config` section with exactly five values; `project_tests` itself is not copied (rule 7) |
| Q-K4-4 | How far back are pull requests read? | open PRs plus the last 8 ISO weeks, `--weeks N` (rule 14) |
| Q-K4-5 | The brief says `issues` are "the metrics and drift issues". The product report (SPEC-0011) is a third issue. | include the label `agk-product-report` too, so the report can link last week's (rule 15) |
| Q-K4-6 | Which directories does the marker search skip? | `.git`, `node_modules`, `vendor`, `target`, `__pycache__`, `.venv` (rule 9). The pilot is a Go module, where `test_dirs = ["."]` would otherwise walk `vendor` |
| Q-K4-7 | Acceptance grammar: split at `; ` only, or also at `. `? | `; ` only (rule 8) |
| Q-K4-8 | A requirement whose acceptance has no `ACn` structure. | `criteria: []`, `criteria_form: "unstructured"`; SPEC-0010 decides what the check does with it (rule 8) |
| Q-K4-9 | A marker run `REQ-001 REQ-002 AC2` attaches `AC2` to both. Is that what a test author means? | yes (1 of 543 markers today); the rule is explicit so it cannot differ by tool (rule 9) |
| Q-K4-10 | "Ruled in the log" is the text `<id> ruled`. Only 33 of 115 ids match; the rest are ruled in notes tables. Should the log convention be tightened (a ruling row names the id and says `ruled`) or should the facts also read `## Rulings` tables? | the narrow definition, so the report never claims a ruling it did not read; the inbox only looks at ids in open places (rule 13, SPEC-0011 rule 4) |
| Q-K4-11 | What makes a question "open" (`open_in`)? | it is named in a Draft spec's notes file, a Proposed ADR, or an `## Open` section of a notes file (rule 13); historical questions in Approved specs' notes drop out |
| Q-K4-12 | A spec or ADR residual bullet has no "closed" state; only the register has a closed table. | bullets are `open`; `closed` appears only for the register's closed table (rule 12). A convention for closing a bullet is a later spec |
| Q-K4-13 | `facts.py` imports `metrics`, `drift_audit`, `check_specs` and `check_adrs`; each must be importable without side effects. | yes, they have `main()` guards; a test imports each (rule 16, 22) |
| Q-K4-14 | The three refactors (rule 17) in the facts PR, or three separate PRs first? | in the facts PR with before-and-after tests, so they cannot land without a user; the maintainers may split them |
| Q-K4-15 | Schema keyword subset and a stdlib validator in the tests. | the list in rule 19 and a validator that fails on any other keyword |
| Q-K4-16 | The schema is kit-only, so a target cannot validate its own document. Is that acceptable? | yes for K4; targets validate through the golden tests that ship in `tests/kit` (rule 19) |
| Q-K4-17 | Who regenerates a golden file? | a person, with a documented command; no test rewrites a golden (rule 20) |
| Q-K4-18 | `files` per pull request costs one API call each. | read for the PRs in the window only; a residual records a cache (rule 14) |
| Q-K4-19 | `today` defaults to the UTC date. The rules say "dates from `date -u`"; a Python script reads the same clock. | `datetime.now(UTC).date()`; `--today` overrides (rule 1) |

## Dependencies on the other K4 specs (read together)

- SPEC-0010 rule 17 defines the `proof` field of a pull request (the outcome of the `proof` job, read from step conclusions); rule 14 of
  this spec carries it. If SPEC-0010 changes how the outcome is transported, rule 14 changes with it.
- SPEC-0010 rules 1 and 2 use `common.parse_acceptance` and `common.find_ac_markers`, defined by rules 8, 9 and 17 here. The grammar
  lives here only; SPEC-0010 repeats it in one sentence and defers to this text.
- SPEC-0011 reads `config.inbox_hours`, `questions[].open_in` and `ruled`, `issues[].label`, and `pull_requests[].created_at`,
  `merged_at`, `files`, `verdicts`, `behaviour` and `proof`; it adds no key to the document. Its rule 4 states which questions are items,
  and relies on rules 11 and 13 here.

## Proof plan

- Criterion e needs two claims: the report derives from the facts, and the facts derive from the repository. This spec proves the
  second with determinism, golden files, `unknown` handling and schema validation of this repository's own document; SPEC-0011
  proves the first (the renderer takes `--facts FILE` and nothing else).
- The first live run is recorded in `docs/runs/` when the engine is built: this repository at `HEAD`, twice, byte-identical, with
  the size and the list of `unknown` sections.

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-16 | SPEC-0009 facts drafted: one script, one JSON document, a fixed key list, `unknown` never a default, imports instead of new parsers, a committed hand-written schema | criterion e of ADR-0021 | `docs/specs/0009-facts.md` | agent |

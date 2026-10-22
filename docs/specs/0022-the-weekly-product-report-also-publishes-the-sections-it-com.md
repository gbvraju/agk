# SPEC-0022: The weekly report also publishes its sections as data in report.json

- Status: Approved
- Owner: reviewer group (a team from config/reviewers.yaml)
- Requirements: REQ-029

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
Written by the intake of one sentence (SPEC-0012): "The weekly product report also publishes the sections it computed as data, in a report.json beside facts.json in the same artifact, so any reader can
show the same report without reimplementing its rules." It is generic and project-agnostic: it holds for every project the kit is installed in and for any reader of the report, and it names no project and no
reader. Evidence: reproducing the report's rules in another program was measured at about 2,300 changed lines; data removes that duplication and the drift it invites.
The maintainers answered 3 questions before it was written: the markdown and the inbox output are byte-identical to before (the goldens do not change) and `report.json` covers the weekly report; an item is data only with no printed text, the item
kinds are a fixed list in this spec each with its fields, and a new kind or field is a schema change (the schema number goes up) so a reader can rely on the list; the artifact keeps the name
`agk-facts-<week>` (renaming would break readers) and holds exactly `facts.json` and `report.json`, the run fails if either is missing, and the later intake for the per-week values and the requirement rows
is due 2026-12-31.

## Rules

1. **One option.** `python3 scripts/agk/product_report.py --facts FILE [--today D] [--week W] --json OUT` prints the markdown report as before and also writes `OUT`, a file `report.json`, from the same facts, in
   the same run, with the same `--today` and `--week`. Without `--json` the script behaves as before and writes no file. `--json` is refused with `--inbox` and with `--print-action`.
2. **The structure comes first.** The script builds one structure from the facts and the day and the week, and renders the markdown from that structure alone; `report.json` is that structure written as JSON. A
   function that takes the structure and nothing else renders the markdown, so a test can render it from the parsed `report.json` and compare it with what the script printed (byte for byte). The inbox output
   (`--inbox`) and the markdown of every existing golden are byte-identical to before; the inbox is built from the same item builders and is not part of `report.json`.
3. **The document.** `report.json` has the keys `schema` (the number 1), `week` (`2026-W41`), `opening`, `sections` and `notices`, and no other. `opening` is `{"first", "last", "as_of"}`, three dates
   (`first` the Monday, `last` the Sunday, `as_of` the day the lists are as of). `sections` has the keys `delivered`, `proven`, `needs_you`, `at_risk` and `cost`, each a list in the order the markdown prints, an
   empty list when the markdown prints `nothing this week`; `needs_you` is a list of groups `{"group", "count", "items"}` in the order of the markdown (`group` one of `spec`, `adr`, `question`, `pull-request`, `residual`, `requirement`; `count` a number or `"unknown"`). `notices` is the
   list of the footer lines in the order printed.
4. **Items.** Every item is an object with `kind` (a word of the list in rule 5), the fields of that kind and nothing else, and `links`: a list of `{"to", "url"}` objects, `to` being `pull-request`, `file`,
   `directory`, `issue` or `search`, in the order the markdown prints them (empty when the line has none). A date is `YYYY-MM-DD`; a number is a JSON number; a title is the text the report prints and is present
   only where the report prints it.
5. **The fixed list of kinds** (the fields of each kind besides `kind` and `links`):

   | Section | `kind` | Fields |
   | --- | --- | --- |
   | delivered | `requirement-done` | `id`, `title`, `criteria` (a list of criterion ids, or `"unknown"`), `became_done` (`"this-week"` or `"unknown"`) |
   | delivered | `pull-request-merged` | `number`, `title`, `merged_on` |
   | delivered | `pull-requests-merged` | `count` (the busy-week line, SPEC-0015) |
   | proven | `requirement-proven` | `id`, `last_change` (`{"number", "proof"}`, `proof` being `proven` or `skipped`) |
   | proven | `requirement-not-proven` | `id`, `reasons` (a list of `{"reason": "criteria-unknown"}`, `{"reason": "no-criteria"}`, `{"reason": "no-test", "ac"}`, `{"reason": "no-merged-change"}`, `{"reason": "not-shown", "number", "proof", "why"}`, `{"reason": "unknown-proof", "number", "proof", "why"}`; `why` is the printed reason word or `"unknown"`) |
   | proven | `planned-not-counted` | `count` |
   | needs_you | `draft-spec` | `id`, `title` |
   | needs_you | `proposed-adr` | `id`, `title` |
   | needs_you | `question` | `id`, `asked_in` |
   | needs_you | `pull-request-no-verdict` | `number`, `title`, `days` |
   | needs_you | `overdue-residual` | `due`, `text` (as printed, shortened) |
   | needs_you | `unspecced-requirement` | `id`, `title` |
   | at_risk | `residual-overdue` | `due`, `days`, `text` (as printed, shortened) |
   | at_risk | `pull-requests-open-long` | `entries` (a list of `{"number", "days"}`, with `title` when the list has one entry) |
   | at_risk | `pull-requests-sent-back` | `entries` (`{"number", "times"}`, with `title` when one) |
   | at_risk | `pull-requests-merged-no-verdict` | `entries` (`{"number"}`; the report prints no title for it) |
   | at_risk | `pull-requests-merged-not-cleared` | `entries` (`{"number"}`; the report prints no title for it) |
   | at_risk | `drift-audit` | `total` (a number or `"unknown"`), `counts` (an object of the finding kinds to numbers or `"unknown"`), `open_issue` (a number, `"none"` or `"unknown"`) |
   | cost | `pull-request-cost` | `number`, `title`, `hours` (a decimal string or `"unknown"`), `fix_verdicts` (a number or `"unknown"`) |
   | cost | `week-totals` | `merged`, `hours`, `fix_verdicts`, `behaviour_unchanged`, `estimate` (`{"within", "counted"}` or `"none-declared"`), `busy` (a boolean) |
   | any section, and `needs_you` groups | `unknown` | `what` (the thing that could not be read: `requirements`, `pull requests`, `test markers`, `questions`, `residuals`, `the drift counts`, `the age limit for pull requests (inbox_hours)`) |
   | notices | `facts-commit` | `commit` |
   | notices | `working-tree-modified` | `dirty` (the printed value) |
   | notices | `kit-version` | `version` (a string or `"unknown"`) |
   | notices | `metrics-issue` | `state` (`found`, `none-found` or `unknown`), and `number`, `title` when found |
   | notices | `drift-audit-issue` | `state` (as above), and `number`, `title` when found |

6. **Unknown stays unknown.** Wherever the facts mark a value `"unknown"`, or a value cannot be read, the field holds the string `"unknown"` and is never a number, a null, a guess or a default; an `unknown`
   item (rule 5) stands where the markdown prints `unknown: <what> could not be read`.
7. **Versioned, and the list is closed.** `schema` is 1. A kind or a field that is not in rule 5 does not exist in schema 1: adding one, or changing a field, raises the number (and this spec is amended).
   `kit/report-schema.json` is a hand-written JSON Schema of rules 3 to 5 (installed verbatim, like `kit/facts-schema.json`), and a test validates every golden `report.json` against it and fails on an extra
   key, an extra kind or a missing field.
8. **Determinism.** The same facts, `--today` and `--week` give a byte-identical `report.json` (keys in the order of rules 3 to 5, two-space indent, UTF-8, a final newline), and a byte-identical markdown.
9. **The artifact.** In the `product-report` workflow the report step writes the markdown and `report.json` in one run of `product_report.py` and before the issue is written. The upload step names the two files
   (`facts.json` and `report.json`, each by its path, no pattern) in the one artifact `agk-facts-<week>`, whose name does not change. `facts.json` is the byte-identical file of SPEC-0019 rule 2. The upload fails
   the run when either file is missing or empty; the issue already written stays (SPEC-0019 rule 4). Retention, the pinned action, the order after the issue, `overwrite` and the `permissions` block are
   unchanged, and the workflow commits, pushes and publishes nothing else.
10. **Generic.** The script, the schema file and the tests name no project and no reader, and read nothing but the facts file; `product_report.py` adds no import (SPEC-0011 rule 13). The links are the ones
    the markdown prints, built from the facts' repository and commit.
11. **How it changes.** SPEC-0011 and SPEC-0019 are Approved: the build changes them by `docs/runs/proposed-spec-amendments-N.md`, applied by its ADR. SPEC-0011 rules 1, 8 to 11, 13, 14 and 18 gain the option, the
    structure and the schema; SPEC-0019 rules 1 to 4 and 8 name the second file. The build is a kit change (a bump, the hashes, the plugin and `agk.toml` versions, an ADR that names the protected classes
    `.github/`, `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`) and the security guide's line for `product-report.yml` names the second file. It is large, and the maintainers' size rule
    applies: it may be split in the brief (the structure and the markdown first, the file and the artifact after).
12. **The tests.** The recorded facts of the report goldens give one `report.json` each; a test renders the markdown from each and compares it with the golden markdown; a test validates each against
    `kit/report-schema.json`; a test builds a facts document with unknown values in every section; a test runs the script twice; the workflow file is read for rule 9; the inbox goldens are unchanged. No
    network and no model.

## Tests

- Rules 1 to 4: `--json` writes the document with the opening, the five sections and the notices, the markdown unchanged; REQ-029 AC1.
- Rule 2: the markdown rendered from the parsed `report.json` equals the printed markdown for every golden facts, and the inbox goldens and the report goldens are unchanged; REQ-029 AC2.
- Rule 6: facts with unknown values give the string `unknown` in every section, never a number or a null; REQ-029 AC3.
- Rules 5 and 7: every golden `report.json` validates against `kit/report-schema.json`; an extra kind, an extra field and a missing field fail; REQ-029 AC4.
- Rule 8: two runs give byte-identical files; REQ-029 AC5.
- Rule 9: the workflow writes both files in the report step, uploads exactly the two paths, fails when either is missing or empty and leaves the issue; REQ-029 AC6.
- Rules 9 and 10: the permissions, retention, pin and order are unchanged and nothing else publishes the files; REQ-029 AC7.
- Rule 10: the script and the schema name no project or reader, add no import and read only the facts file; REQ-029 AC8.

## Proof

REQ-029 AC1 and AC2: *any reader gets the same report as data, and the markdown is rendered from it, so the two cannot differ.* Rules 1 to 4. REQ-029 AC3 to AC5: *unknown stays unknown, the list of kinds is closed
and the file is reproducible.* Rules 6 to 8. REQ-029 AC6 and AC7: *the artifact holds both files and nothing else changes.* Rule 9. REQ-029 AC8: *nothing project-specific.* Rule 10. The first scheduled run after
the build is merged shows both files in the artifact of its run page, and the maintainers download it and compare `report.json` with the issue of that week.

## Residual

- 2026-10-22: the per-week values and the requirement rows are not in `report.json`; a later intake (owner: maintainers) adds them to the same file, as a schema change (due 2026-12-31).
- 2026-10-22: the items carry no printed text, so a reader writes its own sentences from the kinds; the wording of the markdown can change without a schema change, and a reader that copies it can drift (due 2026-12-31).
- 2026-10-22: the structure is built from the facts alone, so a report is only as complete as the facts; a field the facts do not hold is `unknown` (due 2026-12-31).

## Open questions

none

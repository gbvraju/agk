# Notes on SPEC-0011 (decision inbox and weekly product report)

Date: 2026-10-16 (from `date -u`). Overnight brief 3, item C. The spec was written Draft and set **Approved** on the maintainers'
rulings of 2026-10-16 (final commit of the pull request); nothing is implemented and no protected path is changed by this pull request. It is the third of the five K4 specs of ADR-0021 (decision 2) and serves exit
criteria a, d and e. Every question below was raised with a conservative reading and has been ruled (section Rulings); none is open.

## What exists today (read on 2026-10-16, on `main` at 94a807d)

- **Weekly issues.** `metrics.yml` runs Mondays at 06:43 UTC with `issues: write` (and `contents`, `pull-requests`, `checks`, `actions`
  read), lists issues by label with `gh issue list --label agk-metrics --state all`, and chooses `create`/`update N` through
  `metrics.py --print-action`. `drift-audit.yml` runs Saturdays at 06:17 UTC and keeps one open issue labelled `agk-drift-audit`.
  The week of a metrics issue is the full ISO week before `today` (`metrics.window`), titled `agk metrics 2026-Www`.
- **What the facts will hold** (SPEC-0009, not built): requirements with criteria, markers with `ac`, specs and ADRs with status,
  residuals with `due`, questions with `ruled` and `open_in`, pull requests with `verdicts`, `behaviour`, `files` and `proof`
  (SPEC-0010), issues with number, title, label and state, and the `drift` counts per finding kind (added by the ruling on Q-K4-48, in
  SPEC-0009). No pull request body is read except for `Behaviour:`.
- **The inbox, on `main` today (computed by hand for these notes, not by a script).** `Draft` specs: 0 of the first eight, and
  SPEC-0009 to SPEC-0011 once these pull requests merge. `Proposed` ADRs: none. `planned` requirements that no spec names: 11 of 17
  (REQ-004 to REQ-008 and REQ-015 to REQ-020); REQ-005 and REQ-008 are named by Accepted ADRs (ADR-0003, 0004, 0006, 0009), REQ-004,
  REQ-006 and REQ-007 by no spec and no ADR. Overdue residuals: not computed here (the register has 26 open lines).
  Questions: 115 `Q-` ids, 33 with a "ruled" row; none is open in a Draft spec's notes today.
- **The pilot.** The pilot repository exists: a Go module with `go test ./...` as `project_tests`, `test_dirs = ["."]`,
  `test_patterns = ["*_test.go"]`, adopted on kit 0.11.0, ruleset applied, doctor 20 ok. The product owner is the maintainer. This
  repository does not name it. (The draft said it was to be chosen and adopted by 2026-11-02; that text is replaced.)

## Decisions taken in the draft (each is a numbered rule)

- The renderer is a pure function of a facts document (rules 1, 2, 14). Criterion e is proved by tests of the renderer's source and
  behaviour (rule 13), not by a promise.
- The inbox has the six kinds the ADR lists, each defined as a predicate over facts fields with its line template (rules 3 to 6).
  Draft specs and Proposed ADRs are items by status alone. A question is an item only where it is open (rule 4).
- One report per ISO week, five sections with fixed headings and order, every line linked, a `facts: <commit>` footer (rules 7, 8, 11).
- "Proven" is defined without reading a pull request body: a requirement is linked to a pull request through the marker files it
  changed (rule 9). That is an approximation, stated.
- "Cost" is recomputed from the facts in the simplest way (hours open, verdict rounds, declarations); the cost class stays with the
  metrics issue, which the report links (rule 10).
- The action (create or update) is chosen from the facts' issue list, so the renderer still reads only the facts (rule 16).
- Installed by default, as metrics and the drift audit; those and `governance` are untouched (rule 17).

## Options compared

| Question | Option taken | Not taken, and why |
| --- | --- | --- |
| Input of the renderer | only a facts file | facts plus the API (a second reader; criterion e could not be tested); the repository (same) |
| Which week | the week before `today` (as metrics) | the current week (incomplete on Monday); the week of `today` plus the previous (two reports) |
| Link requirement to pull request | the marker files a pull request changed | `Advances:` from the body (typed by an agent; forbidden by criterion e); commit messages (typed text) |
| Cost numbers | recomputed from facts in a few lines, with a consistency test | importing `metrics` (the renderer would then read files); copying metrics' cost class (a second implementation of the class) |
| Inbox length | every item | the top N (an item silently hidden is a miss under criterion d) |
| Idempotence | `--print-action` over `issues[]` | a marker search inside the workflow with `gh` (a read outside the facts) |
| Draft pull requests | not distinguished | exclude drafts (facts do not carry the field in the first design) |

## Questions raised (all ruled; see Rulings)

| Q | Question | Reading taken in the spec |
| --- | --- | --- |
| Q-K4-40 | Does `--today` default to the facts' `today` or to the clock? | the facts' `today`, so the renderer has no clock (rule 1) |
| Q-K4-41 | The report covers the previous ISO week; the inbox is "as of today". Same issue? | yes, one issue, the footer names the facts commit (rules 7, 11) |
| Q-K4-42 | Is a Draft spec an inbox item by status alone, including one the maintainers know they are reviewing? | yes; the item leaves when the status changes (rule 3) |
| Q-K4-43 | A "waiting" question is open in a Draft spec's notes or a Proposed ADR, and not `ruled`. | rule 4; the 82 historical ids with no "ruled" row are not items |
| Q-K4-44 | The inbox shows every item, never the top N. | yes (rule 3) |
| Q-K4-45 | A pull request's age: `days * 24` from the creation date to `today`, because `today` is a date. | rule 5; the error is under a day; `inbox_hours` stays in hours so that a later spec can use times |
| Q-K4-46 | 11 of 17 `planned` requirements have no spec today (5 of them predate specs and are named by ADRs or by nothing). Keep the ADR's definition exactly, or exclude requirements named by an Accepted ADR? | the ADR's definition, unsoftened (rule 6); expect noise until the maintainers choose |
| Q-K4-47 | Last change of a requirement = the latest merged pull request that changed a file carrying one of its markers. | rule 9; file-level, not test-level |
| Q-K4-48 | "Drifting" needs the drift audit's findings; the facts carry the issue's number and title only. | the report links the open drift issue and prints no count (rule 10); a facts addition (a count read from the issue body) would need an amendment of SPEC-0009 |
| Q-K4-49 | "Being reworked" = two or more `fix` verdicts, or any `rejected`. | rule 10 |
| Q-K4-50 | The Cost section recomputes hours and rounds with its own function. | rule 10 and the consistency test of rule 18; metrics move onto the facts later (residual) |
| Q-K4-51 | "Plain language" cannot be checked by a program. | fixed line templates in the golden files, reviewed by the maintainers; no check (rule 8) |
| Q-K4-52 | The doctor checks that the drift workflow is active. Extend it to the product-report workflow? | yes, without a new table row (rule 15); the doctor spec is Approved, so this is an amendment of SPEC-0006 at implementation |
| Q-K4-53 | Workflow permissions: `contents`, `pull-requests`, `checks`, `actions` read and `issues` write, as metrics. | rule 15; `actions: read` is needed for the `proof` job steps |
| Q-K4-54 | Label `agk-product-report`, title `agk product report YYYY-Www`, hidden marker line. | rule 7 |
| Q-K4-55 | An update replaces the issue body; manual edits to the body are lost, comments stay. | rule 16, as metrics |
| Q-K4-56 | A whole facts section that is `"unknown"` prints one line and is counted nowhere. | rule 12 |
| Q-K4-57 | How does the product owner get the report (notification)? | not specified: GitHub issue notifications of the repository; the pilot sets watching |
| Q-K4-58 | The hand count of criterion d: the maintainers list the items before seeing the inbox; the agent compares afterwards. | rule 20 |
| Q-K4-59 | Where the pilot answers are recorded, given that this repository never names the pilot. | `docs/runs/` here, without the pilot's name and without product code (rule 19); the maintainers may choose the pilot's own repository instead |

## Rulings (maintainers, 2026-10-16)

The default ruling is that every reading the draft took is accepted; the table lists each question and the exceptions. Pilot: the
pilot repository now exists and is described above; it is still "the pilot repository" here and never named.

| Q | Ruling | Where in the spec |
| --- | --- | --- |
| Q-K4-40 | accepted as drafted: `--today` defaults to the facts' `today` | rule 1 |
| Q-K4-41 | accepted as drafted: one issue, the footer names the facts commit | rules 7, 11 |
| Q-K4-42 | accepted as drafted: a Draft spec is an item by status alone | rule 3 |
| Q-K4-43 | accepted as drafted: a waiting question is open in a Draft spec's notes or a Proposed ADR and not `ruled` | rule 4 |
| Q-K4-44 | accepted as drafted: the inbox shows every item | rule 3 |
| Q-K4-45 | accepted as drafted: age is whole days times 24 | rule 5 |
| Q-K4-46 | kept: the ADR's definition. The `planned` requirements with no spec are real items: some describe behaviour that already exists while their status still says `planned`. They are cleaned up as K4 work (a docs pull request sets statuses with evidence, or writes the missing spec), not hidden by the inbox | rule 6 |
| Q-K4-47 | accepted as drafted: last change through marker files | rule 9 |
| Q-K4-48 | **ruled (and decided in SPEC-0009, #51):** "At risk" prints the drift counts from the facts' `drift` section and links the open drift issue | rule 10 |
| Q-K4-49 | accepted as drafted: reworked means two or more `fix` verdicts or any `rejected` | rule 10 |
| Q-K4-50 | accepted as drafted: Cost recomputed from the facts, with the consistency test | rule 10, 18 |
| Q-K4-51 | accepted as drafted: plain language by fixed templates in the golden files | rule 8 |
| Q-K4-52 | yes: at implementation, an amendment of SPEC-0006 extends `drift-workflow-state` to also cover the product-report workflow, without a new check id | rule 15 |
| Q-K4-53 | accepted as drafted: the permissions of metrics plus `actions: read` | rule 15 |
| Q-K4-54 | accepted as drafted: label, title and marker | rule 7 |
| Q-K4-55 | accepted as drafted: an update replaces the body | rule 16 |
| Q-K4-56 | accepted as drafted: a whole `"unknown"` section prints one line | rule 12 |
| Q-K4-57 | accepted as drafted: GitHub issue notifications; the pilot sets watching | not in the spec |
| Q-K4-58 | accepted as drafted: the hand count is written before the inbox is shown | rule 20 |
| Q-K4-59 | **changed:** the product owner's answers and the maintainers' marks are recorded **in the pilot's own repository** (`docs/runs/product-report-week-N.md`), committed by the pilot's session through a pull request. This repository records only the score (5 of 5, the week, a link to that file) in `docs/runs/`, with the pilot unnamed | rule 19 |

**Sibling specs touched.** The `drift` section that rule 10 reads is added to SPEC-0009 (#51, rules 3 and 15); this pull request edits
only SPEC-0011. The amendment of SPEC-0006 (Q-K4-52) is made at implementation, not here. Rule 20, the criterion d hand counts, is
accepted as drafted (Q-K4-58); where the pilot's side of those lists is kept was not ruled and the drafted text stands.

## Proof plan

- Criterion e: the renderer's source test and behaviour tests (rule 13), the footer commit (rule 11), and the maintainers' rerun at that
  commit (rule 21).
- Criterion d: two hand counts here and two in the pilot, taken before the inbox is shown (rule 20).
- Criterion a: two scheduled Mondays in the pilot, the product owner's written answers from the issue alone, the maintainers' marks
  (rule 19), both in the pilot's own repository (`docs/runs/product-report-week-N.md`, committed by the pilot's session). This
  repository records only the score, with a link. The agent here never writes or marks an answer.

## Decisions-log rows (for the maintainers' log; not edited in this pull request)

| Date | Decision | Reason | Recorded in | By |
| --- | --- | --- | --- | --- |
| 2026-10-16 | SPEC-0011 inbox and weekly product report Approved: a renderer that reads only the facts document, six inbox kinds, five sections in the order of the five questions, every line linked, a `facts:` footer, one issue per ISO week at Monday 07:13 UTC | criteria a, d, e of ADR-0021 | `docs/specs/0011-inbox-and-report.md` | reviewer |
| 2026-10-16 | Q-K4-40 to Q-K4-59 ruled: every reading of the draft accepted; Q-K4-46 the unspecced `planned` requirements are real items and are cleaned up as K4 work; Q-K4-48 "At risk" prints the drift counts from the facts' `drift` section; Q-K4-52 the doctor's `drift-workflow-state` is extended at implementation without a new check id; Q-K4-59 the pilot answers and marks live in the pilot repository and this repository records only the score | maintainers' rulings of 2026-10-16 on the Draft SPEC-0011 | `docs/runs/spec-0011-notes.md` | reviewer |

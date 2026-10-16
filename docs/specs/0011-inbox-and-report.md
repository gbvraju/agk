# SPEC-0011: decision inbox and weekly product report

- Status: Approved
- Owner: maintainers
- Requirements: REQ-017 (AC1), REQ-018 (AC1, AC2)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
This is the third of the five K4 specs of ADR-0021 and serves exit criteria a, d and e. Its only input is the facts document of
SPEC-0009 (and the field `proof` of SPEC-0010 rule 17). The points `Q-K4-40` to `Q-K4-59` were ruled by
the maintainers on 2026-10-16 (`docs/runs/spec-0011-notes.md`). GitHub facts not reconfirmed are marked `(verify)`. The repository facts quoted here
were read on 2026-10-16.

## Rules

### The renderer and the inbox

1. **Command.** `python3 scripts/agk/product_report.py --facts FILE [--today YYYY-MM-DD] [--week YYYY-Www] [--inbox | --print-action]`.
   Standard library only. Without a mode flag it writes the weekly report (rule 7) to stdout as Markdown; with `--inbox` only the
   inbox (rule 3); with `--print-action` one line, `create` or `update N` (rule 16). `--today` defaults to the `today` of the facts
   document, never to the clock; `--week` defaults to the ISO week before the week of `--today`, as `metrics.window` does. The script
   is vendored into every target and runs without the plugin (SPEC-0005 rule 2).
2. **The only input is the facts document.** The renderer reads the one file named by `--facts` and nothing else: no other file, no
   environment variable, no clock, no `git`, no `gh`, no network (rule 13 tests it). A facts document whose `schema` is not the
   version the renderer knows is a refusal that names the field. Every number and every status the renderer prints is computed from
   the document by the rules below; nothing is typed into it.
3. **The inbox.** The inbox is the list of items that wait for a person. Each item is one line, ends with its link (rule 11), and
   belongs to one of six kinds, listed in this order and, within a kind, in the order of the key shown:

   | Kind | Is an item when (facts fields) | Sorted by | The line |
   | --- | --- | --- | --- |
   | `spec` | `specs[].status` is `Draft` | spec id | `Draft spec SPEC-0009 "<title>" waits for approval` |
   | `adr` | `adrs[].status` is `Proposed` | ADR id | `Proposed ADR-0021 "<title>" waits for a decision` |
   | `question` | rule 4 | question id | `Question Q-K4-1 is waiting, asked in <path>` |
   | `pull-request` | rule 5 | number | `PR #50 "<title>" has had no verdict for N days` |
   | `residual` | `residuals[]` with `state` `open` and `due` before `today` | source, due | `Overdue since <due>: <text, first 120 characters>` |
   | `requirement` | `requirements[].status` is `planned` and no `specs[].requirements` names it | id | `REQ-017 "<title>" is planned and no spec names it` |

   An item carries no judgement and no guess: its line is built from the fields above and the numbers rule 5 computes.
4. **A waiting question.** A `questions[]` object is an item when `open_in` is non-empty and `ruled` is `false`. The link is the first
   path of `open_in`. A question that appears only in the notes of an `Approved` spec, or in an `Accepted` ADR, is history and is not an
   item (SPEC-0009 rule 13). Seven in ten of the 115 `Q-` ids of this repository are not named by a "ruled" row of the decisions log
   (`docs/runs/spec-0009-notes.md`); they are not items, because none is open in a Draft spec's notes or a Proposed ADR.
5. **A pull request without a verdict.** A `pull_requests[]` object is an item when `state` is `open`, `verdicts` is `[]`, and its age is
   at least `inbox_hours` (`config.inbox_hours`, default 48; the key is new in `agk.toml`). The age is `(today - date(created_at))` in days
   times 24; so with 48 a pull request opened two calendar days before `today` or earlier is an item, and one opened yesterday is not
   (Q-K4-45). The line prints the whole days. A draft pull request is not distinguished in K4.
6. **Overdue residuals and unspecced requirements.** A residual with `due` `null` or `"unknown"` is not overdue and is not an item
   (a malformed date is a drift-audit finding, SPEC-0004). A `requirement` item is listed even if the requirement has markers and an
   Accepted ADR names it: the rule is the ADR's, "planned requirements with no spec" (ADR-0021 decision 2), and not softened. On `main`
   today 11 of the 17 `planned` requirements have no spec (Q-K4-46).

### The report

7. **One issue per ISO week.** The title is `agk product report YYYY-Www` for the week the report covers, the label is
   `agk-product-report`, and the body starts with the hidden line `<!-- agk-product-report: YYYY-Www -->` (the marker the action of
   rule 16 looks for). The week covered is the full ISO week before the week of `today`, Monday to Sunday, in UTC, as the metrics issue.
8. **Five sections, in this order, with these headings.** `## Delivered`, `## Proven`, `## Needs you`, `## At risk`, `## Cost`: the
   five questions of ADR-0021, in order. The body has one opening line (the week and the date range), then these five and no other
   `##` heading, then the footer of rule 11. The text is plain language: no abbreviation without its meaning on first use, no field
   names. A section with no line prints `nothing this week`, and that is the only reason for it.
9. **Delivered and Proven.**
   - *Delivered.* One line per requirement whose `status` is `done`: `REQ-001 "<title>" is done: 3 acceptance criteria (AC1, AC2, AC3)`,
     with the link to its section of `docs/requirements.md`; then, one line per pull request with `state` `merged` and `merged_at` in the
     week: `PR #44 "<title>" was merged on <date>`. A requirement counts as delivered by its status alone: the report does not decide
     whether it is done.
   - *Proven.* One line per requirement whose `status` is `done` or `in-progress`. Let n be its criteria and k the criteria that have a
     marker (`markers[]` with `req` and `ac`). Let the *last change* be the merged pull request with the latest `merged_at` whose `files`
     include a file that carries a marker of that requirement (a derived link; no pull request body is read, Q-K4-47). The line is
     `REQ-001 is proven` when k = n and the last change's `proof` is `proven` or `skipped`, and otherwise `REQ-001 is not proven:`
     followed by every reason that holds, in this order: `AC2 has no test`; `the last change (PR #44) was not shown to need its test`
     (`not-proven`); `the last change (PR #44) has an unknown proof` (`unknown`); `no merged change was found` (no related pull request).
     `skipped` is printed as `skipped (declared unchanged)`. `planned` requirements are counted in one closing line, not listed.
10. **Needs you, At risk, Cost.**
    - *Needs you.* The inbox of rule 3, all items, grouped by kind in the order of the table, each group headed by its count.
    - *At risk.* (i) each overdue residual (rule 3's kind, with its days overdue = `today - due`); (ii) each open pull request older
      than 7 days (days = `today - date(created_at)`); (iii) each pull request merged or closed in the week with two or more `fix`
      verdicts or any `rejected` verdict (`was sent back N times`); (iv) the drift counts of the facts' `drift` section (SPEC-0009 rule 15): `drift audit: N findings (D1 a, D2 b, D3 c, D4 d, D5 e, D6 f)`,
      with the link to the open drift-audit issue (`issues[]` with label `agk-drift-audit`); a count that the document marks `"unknown"` is
      printed as `unknown`, and with no open drift issue the line has no link and says `no open drift issue` (ruling on Q-K4-48).
    - *Cost.* For each pull request merged in the week: the hours from `created_at` to `merged_at`, rounded half-up to 0.1 as
      `metrics.hours_between` does, and the number of `fix` verdicts; then the totals for the week: pull requests merged, hours
      (sum), `fix` verdicts, and the number of pull requests that declared `Behaviour: unchanged` (`behaviour` is `"unchanged"`), so
      that overuse of the declaration is visible. The full per-pull-request record, cost class included, stays in that week's metrics issue
      (rule 11); the report does not recompute the class.
11. **Links and the footer.** Every line of every section ends with a link to its evidence: a pull request (`<repo URL>/pull/N`), an
    issue (`<repo URL>/issues/N`), a file at the facts commit (`<repo URL>/blob/<commit>/<path>`), or a commit
    (`<repo URL>/commit/<sha>`), where `<repo URL>` is `https://github.com/` plus `repo` of the document. A document whose `repo` is
    `"unknown"` is a refusal (exit 1): the renderer cannot make a link. The footer is the line `facts: <commit>` (the full SHA), then,
    when `dirty` is not `false`, `the working tree was modified (dirty: <value>)`, then two lines: `metrics: #N "<title>"` for the issue
    labelled `agk-metrics` whose title ends with the week label, and `drift audit: #N "<title>"` for the open `agk-drift-audit` issue; a
    line with no such issue reads `metrics: none found`.
12. **Unknown and dirty are printed.** A value the document marks `"unknown"` is printed as `unknown`, never as zero or empty: a
    section whose source is `"unknown"` (for example `pull_requests` offline) prints one line, `unknown: <section> could not be read`,
    in place of the lines it would have had, and the report counts it nowhere. When `dirty` is not `false` the footer says so (rule 11).
    A criterion with no marker is "no test", and a marker is presence only: the report never says a test is good.
13. **The renderer reads nothing else; the proof of criterion e.** (a) A test feeds each facts document of the fixtures and asserts
    the exact report (golden Markdown). (b) A test reads the source of `product_report.py` with `ast` and fails when it imports a module
    outside `json`, `re`, `sys`, `argparse`, `datetime` (the classes `date` and `timedelta` only), `decimal`, `collections` and
    `pathlib`; when it calls `open`, `input`, `exec`, `eval`, `compile` or `__import__`; when it uses `os`, `subprocess`, `socket`,
    `urllib`, `http`, `shutil`, `tempfile`, `time`; when it calls `datetime.now`, `date.today` or `utcnow`; or when it reads
    `sys.stdin`; and it allows exactly one file read, of the path given by `--facts`. (c) A test runs the renderer in an empty
    temporary directory, with an empty environment and with `HOME` unset, and compares the bytes with the golden. (d) A test changes one number in a facts document and shows that the one line that depends on it changes and no
    other (so no number is constant in the renderer). (e) A test shows that every number in a rendered report can be found, or
    computed by the formulas of rules 5, 9, 10, from the document: it recomputes them with a second, independent function.
14. **Determinism.** The same facts document and the same `--today` and `--week` give byte-identical output: items in the orders of
    the tables, no timestamp, no environment text, `\n` line ends, one trailing newline.

### Schedule and install

15. **The workflow.** `.github/workflows/product-report.yml`, name `product-report`: Mondays at 07:13 UTC (`cron: "13 7 * * 1"`, after
    metrics at 06:43) and `workflow_dispatch` with an optional input `today`. `permissions`: `contents: read`, `pull-requests: read`,
    `checks: read`, `actions: read` (the facts script reads the `proof` runs), `issues: write`. A single job, run only on the default
    branch, SHA-pinned actions as the other workflows, a full checkout. Steps: run `facts.py --today "$today"` into a file in
    `$RUNNER_TEMP`, run `product_report.py --facts` on it, and create or update the issue (rule 16). GitHub may disable scheduled
    workflows after inactivity `(verify)`; the doctor already reports a disabled drift-audit workflow, and at implementation an amendment of SPEC-0006 extends
    `drift-workflow-state` to also cover the product-report workflow, without a new check id (ruling on Q-K4-52).
16. **One issue per week, updated in place.** The step lists the issues labelled `agk-product-report` through the facts document
    (`issues[]`, all states), and `--print-action` prints `create` when none has the week's title, `update N` for the lowest number that has
    it, and `update N` plus a notice line when two do (as metrics). Creating the label is allowed (`gh label create ... || true`).
    A week with no pull request is still written (every section `nothing this week`, the footer present). The existing issue body is
    replaced, not appended.
17. **Installed by default, and nothing else changes.** The workflow and the script are verbatim files of `init` and `adopt`; the
    notice that init and adopt print about workflows with `issues: write` names three workflows instead of two. `metrics.yml`,
    `drift-audit.yml` and `governance.yml` are unchanged, and so are the metrics and drift scripts (ADR-0021 decision 2). A repository
    that does not want the issue deletes the workflow file; the doctor then reports the missing file as it does for the drift audit.

### Tests and proof

18. **Tests.** `tests/kit/test_product_report.py` (installed): the six kinds of rule 3 each on a facts fixture with an item and without;
    the age arithmetic of rule 5 at 47, 48 and 49 hours' worth of days; a question in a Draft notes file, in an Approved one, ruled and
    not; the five sections in order, the empty section text, the unknown text, the dirty footer, the links; the totals of rule 10 against
    the independent function of rule 13(e); the hours rounding against `metrics.hours_between` over the same pairs; `--print-action` with
    none, one and two issues; refusals (wrong `schema`, `repo` `unknown`, a missing file). `tests/kit/test_product_report_workflow.py`:
    name, cron, permissions, default-branch guard, pinned actions, no `pull_request_target`. The tests of rule 13. Fixtures
    `tests/kit/fixtures/report/<case>/` hold `facts.json` and the golden `report.md` and `inbox.md`.
19. **Proof of criterion a (a maintainers' step with the agent's help, not done in this pull request).** In the pilot repository, which
    exists and runs the kit (adopted on kit 0.11.0): for two consecutive ISO weeks the workflow creates the issue on its Monday schedule. For each week the
    product owner (the maintainer) writes, from the issue alone, an answer to each of the five questions, in a file of the **pilot's own repository**, `docs/runs/product-report-week-N.md`,
    committed by the pilot's session through a pull request (ruling on Q-K4-59). The maintainers then check each answer against the pilot repository's own records (its pull requests, its files, its
    issues) and mark it correct or wrong; an answer the report could not give is wrong. The criterion needs 5 of 5 correct in both weeks.
    **What the agent of this repository does:** it records the score only, in `docs/runs/` here (for example `5 of 5, week N, link to
    that file`), with the pilot unnamed; it may run the facts script and the renderer at the facts commit named in the footer, so that the
    maintainers can reproduce the issue. **What it never does:** it does not write an answer, does not read the pilot's product code, and
    does not mark an answer correct. The answers and the maintainers' marks are the record, and they live in the pilot repository.
20. **Proof of criterion d.** On two weekly hand counts in this repository and two in the pilot: on a day the maintainers choose, before
    seeing the inbox, they list by hand every item that waits for them (specs, ADRs, questions, pull requests, overdue residuals,
    unspecced requirements), and send the list to the agent; only then does the agent run `facts.py` and `product_report.py --inbox` at the
    same moment and put both lists side by side in `docs/runs/`. The criterion is met when the inbox misses no item of the hand count; an
    extra item is a finding to read, not a failure. The agent does not edit the inbox to match.
21. **Proof of criterion e.** Rule 13, and the footer `facts: <commit>` of every report; the maintainers may rerun
    `facts.py` at that commit and `product_report.py` on it and diff the result against the issue.
22. **Installed files and classes.** Installed (verbatim): `scripts/agk/product_report.py`, `.github/workflows/product-report.yml`,
    `tests/kit/test_product_report.py`, `tests/kit/test_product_report_workflow.py`, the fixtures, the change to `scripts/agk/init.py`
    (kit-only) for the notice, the doctor's workflow check (`scripts/agk/doctor.py`), and `agk.toml` templates gain `inbox_hours = 48`.
    The classes touched are `scripts/agk/`, `.github/`, `tests/kit/`, `kit/` and `tests/kit_dev/`; the implementation pull request
    carries an ADR that names each. The kit version is bumped.
23. **Order.** Built after SPEC-0009 and SPEC-0010 (ADR-0021 decision 7: inbox and report by 2026-11-23). SPEC-0012 (intake) and
    SPEC-0013 (playbook) do not read this spec's output.

## Tests

- Rules 1 to 6, 18 (inbox): `tests/kit/test_product_report.py`, marker `REQ-017 AC1`.
- Rules 7 to 12, 14, 16, 18 (report): the same file, marker `REQ-018 AC2`; the workflow rules 15, 17: `tests/kit/test_product_report_workflow.py`,
  marker `REQ-018 AC1`.
- Rule 13: the same file, marker `REQ-018 AC2`.
- Rules 19, 20: records in `docs/runs/`, checked by the maintainers, not by a test (markers `REQ-018 AC1` and `REQ-017 AC1`).

## Proof

ADR-0021 exit criterion a: *for two consecutive ISO weeks the weekly product report is created on schedule in the pilot repository, and
for each week the product owner writes answers to the five questions from the report alone; the maintainers check each answer against the
repository and record 5 of 5 correct both weeks.* Rules 7 to 12, 15, 16, 19.

Exit criterion d: *on two weekly hand counts in this repository and two in the pilot, the inbox misses zero items.* Rules 3 to 6, 20.

Exit criterion e: *a test shows every number and every status in the report is computed from the facts document, and the report names the
facts commit; no field is read from a PR body except the `Behaviour:` and `Verdict:` lines.* Rules 2, 13, 21, with SPEC-0009.

## Residual

- 2026-10-16: the report links last change to requirement through files that carry a marker; a requirement whose tests live in a file
  that no pull request changed has "no merged change was found" (due 2026-12-31).
- 2026-10-16: a pull request that was cleared and then received new commits is not an inbox item (its verdict exists); the inbox does
  not see stale verdicts (due 2026-12-31).
- 2026-10-16: the report counts hours and verdicts from the facts, and the metrics issue counts them with its own reader; a difference
  between the two is a defect to be found by the comparison test of rule 18, and closes when metrics move onto the facts (due 2027-01-31).
- 2026-10-16: whether GitHub disables the scheduled workflow after 60 days without repository activity is `(verify)` against current
  documentation (due 2026-11-23).
- 2026-10-16: no product-owner guide is written here; ADR-0021 criterion f (README and one-page guide) is a separate item
  (due 2026-12-14).

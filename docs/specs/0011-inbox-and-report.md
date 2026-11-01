# SPEC-0011: decision inbox and weekly product report

- Status: Approved
- Owner: maintainers
- Requirements: REQ-017 (AC1), REQ-018 (AC1, AC2)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
This is the third of the five K4 specs of ADR-0021 and serves exit criteria a, d and e. Its only input is the facts document of
SPEC-0009 (and the field `proof` of SPEC-0010 rule 17). The points `Q-K4-40` to `Q-K4-60` were ruled by
the maintainers on 2026-10-16 (`docs/runs/spec-0011-notes.md`). GitHub facts not reconfirmed are marked `(verify)`. The repository facts quoted here
were read on 2026-10-16.

## Rules

### The renderer and the inbox

1. **Command.** `python3 scripts/agk/product_report.py --facts FILE [--today YYYY-MM-DD] [--week YYYY-Www] [--inbox | --print-action]`.
   Standard library only. Without a mode flag it writes the weekly report (rule 7) to stdout as Markdown; with `--inbox` only the
   inbox (rule 3); with `--print-action` one line, `create` or `update N` (rule 16). `--today` defaults to the `today` of the facts
   document, never to the clock; `--week` defaults to the ISO week before the week of `--today`, as `metrics.window` does. The script
   is vendored into every target and runs without the plugin (SPEC-0005 rule 2). With `--json FILE` it also writes `report.json`, the structure of the report as data (SPEC-0022 rule 1); `--json` is refused with `--inbox` and `--print-action`.
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
5. **A pull request without a verdict.** A `pull_requests[]` object is an item when `state` is `open`, `verdicts` is `[]` (no comment by a listed verdict author is a verdict, SPEC-0021 rule 5), and its age is
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
   names. A section with no line prints `nothing this week`, and that is the only reason for it. The report is built as a structure of items and rendered from it (SPEC-0022 rules 2 to 5): the opening, every section and the footer (the notices) are items of the fixed kinds, Needs you being groups of items, and the inbox prints the same groups; the printed text does not change.
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
     (`not-proven`; followed by the reason in parentheses, `(not-proven: red-on-head, the tests fail on the change itself)`, or `(not-proven: reason unknown)`); `the last change (PR #44) has an unknown proof` (`unknown`; the same form); `no merged change was found` (no related pull request).
     `skipped` is printed as `skipped (declared unchanged)`. `planned` requirements are counted in one closing line, not listed.
10. **Needs you, At risk, Cost.**
    - *Needs you.* The inbox of rule 3, all items, grouped by kind in the order of the table, each group headed by its count.
    - *At risk.* (i) each overdue residual (rule 3's kind, with its days overdue = `today - due`); (ii) each open pull request older
      than 7 days (days = `today - date(created_at)`); (iii) each pull request merged or closed in the week with two or more `fix`
      verdicts or any `rejected` verdict (`was sent back N times`); (iv) the drift counts of the facts' `drift` section (SPEC-0009 rule 15): `drift audit: N findings (D1 a, D2 b, ...)`, one count for every kind that `drift.counts` holds (`D1` to `D7` today), in order,
      with the link to the open drift-audit issue (`issues[]` with label `agk-drift-audit`); a count that the document marks `"unknown"` is
      printed as `unknown`, and with no open drift issue the line has no link and says `no open drift issue` (ruling on Q-K4-48);
      (v) each pull request merged in the week whose last `Verdict: cleared` names a commit other than its merged `head`, or that has no verdict line: `PR #N was merged before its last commit was cleared` or `PR #N was merged with no verdict`, derived from `pull_requests[].head`, `merged_at` and `verdicts` (a head or verdicts the facts mark `"unknown"` print no line, and a pull request whose `head_cleared` is `yes` prints none, SPEC-0021 rule 7). It reports after the fact and blocks nothing (SPEC-0013 rule 18).
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
    computed by the formulas of rules 5, 9, 10, from the document: it recomputes them with a second, independent function. (f) A test renders the markdown from the structure alone, also after a trip through JSON, and compares it with what the script prints. (g) With `--json` the script writes that one file and nothing else; without it, it writes none (SPEC-0022 rules 1 and 10).
14. **Determinism.** The same facts document and the same `--today` and `--week` give byte-identical output: items in the orders of
    the tables, no timestamp, no environment text, `\n` line ends, one trailing newline. The same holds for `report.json` (SPEC-0022 rule 8).

### Schedule and install

15. **The workflow.** `.github/workflows/product-report.yml`, name `product-report`: Mondays at 07:13 UTC (`cron: "13 7 * * 1"`, after
    metrics at 06:43) and `workflow_dispatch` with an optional input `today`. `permissions`: `contents: read`, `pull-requests: read`,
    `checks: read`, `actions: read` (the facts script reads the `proof` runs), `issues: write`. A single job, run only on the default
    branch, SHA-pinned actions as the other workflows, a full checkout. Steps: run `facts.py --today "$today"` into a file in
    `$RUNNER_TEMP`, run `product_report.py --facts` on it, and create or update the issue (rule 16); then one more step uploads that same facts file as the workflow artifact `agk-facts-<week>` (SPEC-0019), with no new permission. GitHub may disable scheduled
    workflows after inactivity `(verify)`; the doctor already reports a disabled drift-audit workflow, and at implementation an amendment of SPEC-0006 extends
    `drift-workflow-state` to also cover the product-report workflow, without a new check id (ruling on Q-K4-52).
16. **One issue per week, updated in place.** The step lists the issues labelled `agk-product-report` through the facts document
    (`issues[]`, all states), and `--print-action` prints `create` when none has the week's title, `update N` for the lowest number that has
    it, and `update N` plus a notice line when two do (as metrics). Creating the label is allowed (`gh label create ... || true`).
    A week with no pull request is still written (every section `nothing this week`, the footer present). The existing issue body is
    replaced, not appended.
17. **Installed by default, and nothing else changes.** The workflow and the script are verbatim files of `init` and `adopt`; the
    notice that init and adopt print about workflows with `issues: write` names three workflows instead of two, and a second line warns that they need Issues enabled on the repository (`agk doctor` checks it, SPEC-0006). `metrics.yml`,
    `drift-audit.yml` and `governance.yml` are unchanged, and so are the metrics and drift scripts (ADR-0021 decision 2). A repository
    that does not want the issue deletes the workflow file; the doctor then reports the missing file as it does for the drift audit.

### Tests and proof

18. **Tests.** `tests/kit/test_product_report.py` (installed): the six kinds of rule 3 each on a facts fixture with an item and without;
    the age arithmetic of rule 5 at 47, 48 and 49 hours' worth of days; a question in a Draft notes file, in an Approved one, ruled and
    not; the five sections in order, the empty section text, the unknown text, the dirty footer, the links; the totals of rule 10 against
    the independent function of rule 13(e); the hours rounding against `metrics.hours_between` over the same pairs; `--print-action` with
    none, one and two issues; refusals (wrong `schema`, `repo` `unknown`, a missing file). `tests/kit/test_product_report_workflow.py`:
    name, cron, permissions, default-branch guard, pinned actions, no `pull_request_target`. The tests of rule 13. Fixtures
    `tests/kit/fixtures/report/<case>/` hold `facts.json` and the golden `report.md` and `inbox.md`. The tests of SPEC-0022: `tests/kit/test_report_structure.py`, `tests/kit/test_report_json.py` (installed) and `tests/kit_dev/test_report_wiring.py` (kit-only).
19. **Proof of criterion a (a maintainers' step with the agent's help, not done in this pull request).** In the pilot repository, which
    exists and runs the kit (adopted on kit 0.11.0): for two consecutive ISO weeks the workflow creates the issue on its Monday schedule. For each week the
    product owner (the maintainer) writes, from the issue alone, an answer to each of the five questions, in a file of the **pilot's own repository**, `docs/runs/product-report-week-N.md`,
    committed by the pilot's session through a pull request (ruling on Q-K4-59). The maintainers then check each answer against the pilot repository's own records (its pull requests, its files, its
    issues) and mark it correct or wrong; an answer the report could not give is wrong. The criterion needs 5 of 5 correct in both weeks.
    **What the agent of this repository does:** it records the score only, in `docs/runs/` here (for example `5 of 5, week N, link to
    that file`), with the pilot unnamed; it may run the facts script and the renderer at the facts commit named in the footer, so that the
    maintainers can reproduce the issue. **What it never does:** it does not write an answer, does not read the pilot's product code, and
    does not mark an answer correct. The answers and the maintainers' marks are the record, and they live in the pilot repository.
20. **Proof of criterion d.** On two weekly hand counts in this repository and two in the pilot. On a day the maintainers choose, before
    seeing the inbox, they list by hand every item that waits for them (specs, ADRs, questions, pull requests, overdue residuals,
    unspecced requirements); only then is the inbox produced with `facts.py` and `product_report.py --inbox` at the same moment, and both
    lists are put side by side. The criterion is met when the inbox misses no item of the hand count; an extra item is a finding to read,
    not a failure. The inbox is never edited to match.
    - *This repository's two counts* stay as drafted: the maintainers send their list to the agent, who runs the two scripts and records
      both lists side by side in this repository's `docs/runs/`.
    - *The pilot's two counts* (ruling on Q-K4-60) live in the pilot repository: the hand-count list and the inbox side by side are in the
      pilot's own `docs/runs/`, committed by the pilot session through a pull request, like the answers of rule 19. This repository's
      `docs/runs/` records, per pilot week, only: the week, `match` or `mismatch` for each count, and a link to the pilot's file, with the
      pilot unnamed. A count is `match` when the inbox misses no item of the hand count.
21. **Proof of criterion e.** Rule 13, and the footer `facts: <commit>` of every report; the maintainers may rerun
    `facts.py` at that commit and `product_report.py` on it and diff the result against the issue.
22. **Installed files and classes.** Installed (verbatim): `scripts/agk/product_report.py`, `.github/workflows/product-report.yml`,
    `tests/kit/test_product_report.py`, `tests/kit/test_product_report_workflow.py`, the fixtures, the change to `scripts/agk/init.py`
    (kit-only) for the notice, the doctor's workflow check (`scripts/agk/doctor.py`), and `agk.toml` templates gain `inbox_hours = 48`.
    The classes touched are `scripts/agk/`, `.github/`, `tests/kit/`, `kit/` and `tests/kit_dev/`; the implementation pull request
    carries an ADR that names each. The kit version is bumped.
23. **Order.** Built after SPEC-0009 and SPEC-0010 (ADR-0021 decision 7: inbox and report by 2026-11-23). SPEC-0012 (intake) and
    SPEC-0013 (playbook) do not read this spec's output.

### From SPEC-0014: The weekly product report footer names the kit version

Moved from SPEC-0014 by proposed spec amendments 108 (ADR-0244), the text of each rule unchanged. In this section a bare `rule N` means SPEC-0014 rule N, and SPEC-0014 rule N is rule N + 23 here; the tests, proof, residuals and rulings of these rules stay in SPEC-0014.

24. **The facts carry the version.** The facts document gains an optional top-level property `kit_version`: the version string, or `"unknown"` when it cannot be
   read. `schema` stays `1`: no released consumer reads the property (as for `path` and `proof_reason`), and a renderer that does not know it ignores it.
25. **One reader of the installed version.** The installed version is read by one function of `common.py`: the `version` of `agk.toml`, or, when `agk.toml` is absent, the
   `version` of the legacy `[tool.agk]` table of `pyproject.toml` (the stamp of kits 0.1.0 and 0.2.0). `facts.py` calls it, and `upgrade.py` calls it for the stamp it
   already reads; the output of `upgrade.py` on the existing fixtures is byte-identical before and after. `upgrade.py` is not installed, so the function lives in
   `common.py`.
26. **Unknown, never a guess.** A missing file, an unreadable file, a missing `version` key or a value that is not a string gives `"unknown"`. Nothing falls back to a
   constant, to the kit's manifest or to the version of the script that renders.
27. **The footer line.** The weekly report prints `kit version: <value>` as the line directly after the `facts:` line of the footer, where `<value>` is the facts'
   `kit_version`, or `unknown` when the facts carry none (a document made before this rule). The line has no link: its evidence is the facts commit named above it.
28. **The renderer stays pure.** `product_report.py` reads the facts file and no other file, and its imports are unchanged (SPEC-0011 rule 13). The inbox output has no
   `kit version:` line and does not change.

### From SPEC-0015: A busy week's report links the full list of merged pull requests

Moved from SPEC-0015 by proposed spec amendments 108 (ADR-0244), the text of each rule unchanged. In this section a bare `rule N` means SPEC-0015 rule N, and SPEC-0015 rule N is rule N + 28 here; the tests, proof, residuals and rulings of these rules stay in SPEC-0015.

29. **A busy week.** A week is busy when more than ten pull requests merged in it, counted as `merged_in_week` selects them (`state` `merged` and `merged_at` inside the report's week). Ten is one
   named constant in `product_report.py`, not a setting, not read from `agk.toml` and not carried by the facts. Ten or fewer is a quiet week.
30. **A quiet week is unchanged.** For a quiet week the report is byte-identical to what the same facts gave before this change. The existing report goldens are the test; the boundary is tested at
   exactly ten (unchanged) and at eleven (collapsed).
31. **Delivered in a busy week.** Every requirement whose `status` is `done` is still listed, in the same order and with the same lines as today. The lines `PR #N "<title>" was merged on <day>` are not
   printed. In their place there is one line after the requirements: `<N> pull requests were merged this week` (`N` the number of pull requests merged in the week), ending with the week link of rule 5.
32. **Cost in a busy week.** No line is printed for a single pull request. The totals line `This week: ...` is printed with its text exactly as today (with the ending of SPEC-0018 rule 6) and ends with the week link of rule 5 instead of the
   link to all merged pull requests. It is the only line of the section.
33. **The week link.** `<repo URL>/pulls?q=is%3Apr+is%3Amerged+merged%3A<start>..<end>`, where `<repo URL>` is `https://github.com/` plus `repo` of the facts and `<start>` and `<end>` are the Monday
   and the Sunday of the report's week in UTC, `YYYY-MM-DD`, the dates of the opening line. It is built from `repo` and those two dates only (Q-S0015-1).
34. **Nothing else changes.** Proven, Needs you and At risk are unchanged: every pull request that At risk or Needs you named is still named (a pull request sent back, merged without a verdict or
   merged before its last commit was cleared stays in At risk). The footer, the inbox output and the metrics issue are unchanged.
35. **The renderer stays pure.** `product_report.py` reads the facts file and no other file, and its imports are unchanged (SPEC-0011 rule 13).
36. **Unknown is not a count.** When the facts mark `pull_requests` `"unknown"` the report prints today's unknown line and does not collapse; the count of rule 1 is made only from known rows.

### From SPEC-0016: At risk shows one line per kind of pull request risk

Moved from SPEC-0016 by proposed spec amendments 108 (ADR-0244), the text of each rule unchanged. In this section a bare `rule N` means SPEC-0016 rule N, and SPEC-0016 rule N is rule N + 36 here; the tests, proof, residuals and rulings of these rules stay in SPEC-0016.

37. **The four kinds.** The kinds are the lines of `at_risk` that name one pull request: *open too long* (an open pull request older than `OLD_PULL_REQUEST_DAYS`), *sent back* (closed in the week with two or
   more fix verdicts or a rejected one), *merged with no verdict* and *merged before its last commit was cleared*. The overdue-residual lines and the drift line are not kinds of this rule and are printed as today.
38. **One pull request stays as today.** A kind with exactly one pull request prints the line printed before this change, byte for byte (its title, its value and its link).
39. **Two or more become one line.** A kind with two or more pull requests prints one line that names every one of them: `PR` becomes `PRs`, the numbers are in ascending order, separated by `, ` and the
   last by ` and `, each number written as its own link to that pull request (`[#12](<pull request URL>)`), never a range, and the line has no trailing link of its own.
40. **The grouped wording.** Open too long: `PRs #12 (41 days), #15 (30 days) and #20 (9 days) have been open`. Sent back: `PRs #12 (3 times) and #15 (2 times) were sent back`. Merged with no verdict:
   `PRs #12, #15 and #20 were merged with no verdict`. Merged before cleared: `PRs #12 and #15 were merged before their last commit was cleared`. A value in brackets is the one the single line prints
   (`plural(days, "day", "days")` of the pull request, `plural(fixes + rejected, "time", "times")`). A grouped line prints no title (Q-S0016-1).
41. **Every pull request is still named.** The set of pull request numbers that appear in the At risk section is the same as before this change. No number is dropped, merged into a range or replaced by a count.
42. **Where a grouped line stands.** The lines keep the order of today's section: residuals, open too long, sent back, the drift line, then the merged pull requests. A grouped line takes the place of the
   line of its lowest-numbered pull request. So when no kind has two or more pull requests, the section is byte-identical to today's.
43. **Nothing else changes.** Delivered, Proven, Needs you, Cost, the footer, the inbox output and the metrics issue are byte-identical to the report of the same facts before this change.
44. **The renderer stays pure.** `product_report.py` reads the facts file and no other file, and its imports are unchanged (SPEC-0011 rule 13). The number of pull requests of a kind is counted from the
   facts rows only.
45. **Unknown is not a count.** When the facts mark `pull_requests` `"unknown"`, At risk prints today's unknown line and does not group.
46. **Goldens.** The quiet-week goldens change only in At risk, and only where a kind has two or more pull requests; the implementation pull request shows the diff of each golden in its body.

### From SPEC-0017: Delivered lists only the requirements that became done in the week

Moved from SPEC-0017 by proposed spec amendments 108 (ADR-0244), the text of each rule unchanged. In this section a bare `rule N` means SPEC-0017 rule N, and SPEC-0017 rule N is rule N + 46 here; the tests, proof, residuals and rulings of these rules stay in SPEC-0017.

47. **The date a requirement became done.** For each requirement, `facts.py` reads the first-parent history of the default branch for the commits that changed the requirement's `Status:` line in
   `docs/requirements.md`, and takes the latest one whose change set the status to `done` (a requirement added already `done` counts as that commit). The field is `done_on` on the requirement's row, the
   commit's committer date in UTC, `YYYY-MM-DD`. It is `unknown` when no such commit is found, the history is shallow or git cannot read it. It is computed from the repository's history only: no clock, no
   network, no pull request lookup.
48. **The schema.** `schema` stays 1. `done_on` is optional: a facts document without it is valid, and the renderer reads a missing `done_on` as `unknown` (no migration of old facts).
49. **Delivered lists the week's requirements.** A requirement whose `status` is `done` and whose `done_on` is a date inside the report's week (the same Monday and Sunday, in UTC, as the report's opening
   line) is listed with the line printed before this change. One whose `done_on` is a date outside the week is not listed.
50. **Unknown stays visible.** A requirement whose `status` is `done` and whose `done_on` is `unknown` or missing is listed with its usual line followed by ` (week it became done: unknown)`, before the link. It
   is never dropped.
51. **A week with nothing newly done.** Delivered prints no requirement line. Its pull request lines (a quiet week) or the single busy-week line (SPEC-0015) are unchanged. A requirement whose `status` is not
   `done` is not listed, as before.
52. **The workflow reads enough history.** The `product-report` workflow checks out the full history (`fetch-depth: 0`). A test reads the workflow file and fails if its checkout does not set `fetch-depth: 0`,
   so a shallow clone cannot turn every done requirement into `unknown`. (`facts.py` still writes `unknown` for a shallow history; it never guesses a date.)
53. **Nothing else changes.** Proven, Needs you, At risk, Cost, the footer, the inbox output and the metrics issue are byte-identical to the report of the same facts before this change. The quiet-week and
   busy-week goldens change only in Delivered; the implementation pull request shows the diff of each.
54. **The renderer stays pure.** `product_report.py` reads the facts file and no other file, and its imports are unchanged (SPEC-0011 rule 13). The week of a requirement is decided from `done_on` alone.
55. **Unknown is not a date.** When the facts mark `requirements` `"unknown"`, Delivered prints today's unknown line.

### From SPEC-0019: The weekly report publishes the facts it was rendered from

Moved from SPEC-0019 by proposed spec amendments 108 (ADR-0244), the text of each rule unchanged. In this section a bare `rule N` means SPEC-0019 rule N, and SPEC-0019 rule N is rule N + 55 here; the tests, proof, residuals and rulings of these rules stay in SPEC-0019.

56. **One artifact per run.** After the step that writes the issue, the `product-report` workflow has a step that uploads the facts as a workflow artifact named `agk-facts-<week>`, `<week>` being the week label of
   the report (`2026-W42`, the label of the issue title; the first line of the report names it). The artifact holds one file, `facts.json`. From SPEC-0022 the artifact also holds `report.json` (rule 9 there).
57. **The same file.** The file is the facts document that `product_report.py` read for that report, byte for byte: it is the path the workflow wrote with `facts.py`, uploaded as it is, not regenerated, filtered,
   renamed inside the artifact or given another field.
58. **The step.** The upload action is pinned by a full commit SHA with its tag in a comment, like the checkout (SPEC-0011 rule 17); the path is that one file and no pattern; `retention-days` is 90, stated in the
   workflow; `if-no-files-found` is `error`. The step comes after the step that writes the issue, and the week label reaches it from the report step as a step output (Q-S0019-2). From SPEC-0022 the upload names two files, `facts.json` and `report.json`, each by its path, and no pattern.
59. **A failed upload fails the run.** A missing or empty facts file, or an upload that errors, fails the run; the issue already written is not changed or removed. A run for which the issue could not be written does
   not upload (the earlier step failed). The same holds for `report.json` (SPEC-0022 rule 9).
60. **A re-run.** A re-run of the workflow for the same week produces the artifact again under the same name, and the artifact of the latest run is the one used; the upload replaces an artifact of that name in the
   same run and the workflow deletes no other artifact (Q-S0019-1).
61. **Access is GitHub's.** The artifact is readable by those who can read the repository's workflow runs: on a public repository anyone signed in to GitHub, on a private one those who can read it, and by the API
   with a token that can. There is no anonymous download, no sharing mechanism, no release, no page and no other place; the workflow publishes the file nowhere but as a workflow artifact.
62. **No new permission, no new write.** The `permissions` block is what SPEC-0011 rule 15 gave (`contents`, `pull-requests`, `checks` and `actions` read, `issues` write); the workflow commits and pushes nothing and
   writes nothing to the repository but the issue and the label as before.
63. **Nothing else changes.** `facts.py`, `product_report.py`, the report, the issue and its label, the inbox output and the metrics workflow are byte-identical to before. The workflow's header comment says the
   facts are also uploaded, and its "only writes" sentence names the artifact (SPEC-0011 rule 15 is amended for that). With SPEC-0022, `product_report.py` gains `--json` and the report step of the workflow uses it.
64. **How it changes.** The workflow is a verbatim kit file, so the build is a kit change: a bump, the hashes, and an ADR that names the protected classes it touches. SPEC-0011 is Approved; the build changes it by an
   amendment file `docs/runs/proposed-spec-amendments-N.md`, applied by that ADR. The security guide's account of what each workflow may write gains a line for the artifact.
65. **The test.** A test reads the workflow file and fails when the upload step is missing, comes before the step that writes the issue, uploads anything but that one file, names the artifact otherwise than
    `agk-facts-<week>`, omits the 90-day retention or `if-no-files-found: error`, is not pinned by a full commit SHA, or when the permissions differ from rule 7. No network is used.

### From SPEC-0022: The weekly report also publishes its sections as data in report.json

Moved from SPEC-0022 by proposed spec amendments 108 (ADR-0244), the text of each rule unchanged. In this section a bare `rule N` means SPEC-0022 rule N, and SPEC-0022 rule N is rule N + 65 here; the tests, proof, residuals and rulings of these rules stay in SPEC-0022.

66. **One option.** `python3 scripts/agk/product_report.py --facts FILE [--today D] [--week W] --json OUT` prints the markdown report as before and also writes `OUT`, a file `report.json`, from the same facts, in
   the same run, with the same `--today` and `--week`. Without `--json` the script behaves as before and writes no file. `--json` is refused with `--inbox` and with `--print-action`.
67. **The structure comes first.** The script builds one structure from the facts and the day and the week, and renders the markdown from that structure alone; `report.json` is that structure written as JSON. A
   function that takes the structure and nothing else renders the markdown, so a test can render it from the parsed `report.json` and compare it with what the script printed (byte for byte). The inbox output
   (`--inbox`) and the markdown of every existing golden are byte-identical to before; the inbox is built from the same item builders and is not part of `report.json`.
68. **The document.** `report.json` has the keys `schema` (the number 2 since SPEC-0024), `week` (`2026-W41`), `opening`, `sections` and `notices`, and no other. `opening` is `{"first", "last", "as_of"}`, three dates
   (`first` the Monday, `last` the Sunday, `as_of` the day the lists are as of). `sections` has the keys `delivered`, `proven`, `needs_you`, `at_risk` and `cost`, each a list in the order the markdown prints, an
   empty list when the markdown prints `nothing this week`; `needs_you` is a list of groups `{"group", "count", "items"}` in the order of the markdown (`group` one of `spec`, `adr`, `question`, `pull-request`, `residual`, `requirement`; `count` a number or `"unknown"`). `notices` is the
   list of the footer lines in the order printed.
69. **Items.** Every item is an object with `kind` (a word of the list in rule 5), the fields of that kind and nothing else, and `links`: a list of `{"to", "url"}` objects, `to` being `pull-request`, `file`,
   `directory`, `issue` or `search`, in the order the markdown prints them (empty when the line has none). A date is `YYYY-MM-DD`; a number is a JSON number; a title is the text the report prints and is present
   only where the report prints it.
70. **The fixed list of kinds** (the fields of each kind besides `kind` and `links`):

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
   | cost | `week-totals` | `merged`, `hours`, `hours_unknown` (a number, how many of the week's merged pull requests have the hours `unknown`; SPEC-0024), `fix_verdicts`, `behaviour_unchanged`, `estimate` (`{"within", "counted"}` or `"none-declared"`), `busy` (a boolean) |
   | any section, and `needs_you` groups | `unknown` | `what` (the thing that could not be read: `requirements`, `pull requests`, `test markers`, `questions`, `residuals`, `the drift counts`, `the age limit for pull requests (inbox_hours)`) |
   | notices | `facts-commit` | `commit` |
   | notices | `working-tree-modified` | `dirty` (the printed value) |
   | notices | `kit-version` | `version` (a string or `"unknown"`) |
   | notices | `metrics-issue` | `state` (`found`, `none-found` or `unknown`), and `number`, `title` when found |
   | notices | `drift-audit-issue` | `state` (as above), and `number`, `title` when found |
71. **Unknown stays unknown.** Wherever the facts mark a value `"unknown"`, or a value cannot be read, the field holds the string `"unknown"` and is never a number, a null, a guess or a default; an `unknown`
   item (rule 5) stands where the markdown prints `unknown: <what> could not be read`.
72. **Versioned, and the list is closed.** `schema` is 2 (SPEC-0024 added a field to `week-totals`; it was 1). A kind or a field that is not in rule 5 does not exist in schema 2: adding one, or changing a field, raises the number (and this spec is amended).
   `kit/report-schema.json` is a hand-written JSON Schema of rules 3 to 5 (kit-only, not installed, like `kit/facts-schema.json`; its test is `tests/kit_dev/test_report_wiring.py`), and a test validates every golden `report.json` against it and fails on an extra
   key, an extra kind or a missing field.
73. **Determinism.** The same facts, `--today` and `--week` give a byte-identical `report.json` (keys in the order of rules 3 to 5, two-space indent, UTF-8, a final newline), and a byte-identical markdown.
74. **The artifact.** In the `product-report` workflow the report step writes the markdown and `report.json` in one run of `product_report.py` and before the issue is written. The upload step names the two files
   (`facts.json` and `report.json`, each by its path, no pattern) in the one artifact `agk-facts-<week>`, whose name does not change. `facts.json` is the byte-identical file of SPEC-0019 rule 2. The upload fails
   the run when either file is missing or empty; the issue already written stays (SPEC-0019 rule 4). Retention, the pinned action, the order after the issue, `overwrite` and the `permissions` block are
   unchanged, and the workflow commits, pushes and publishes nothing else.
75. **Generic.** The script, the schema file and the tests name no project and no reader, and read nothing but the facts file; `product_report.py` adds no import (SPEC-0011 rule 13). The links are the ones
    the markdown prints, built from the facts' repository and commit.
76. **How it changes.** SPEC-0011 and SPEC-0019 are Approved: the build changes them by `docs/runs/proposed-spec-amendments-N.md`, applied by its ADR. SPEC-0011 rules 1, 8 to 11, 13, 14 and 18 gain the option, the
    structure and the schema; SPEC-0019 rules 1 to 4 and 8 name the second file. The build is a kit change (a bump, the hashes, the plugin and `agk.toml` versions, an ADR that names the protected classes
    `.github/`, `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`) and the security guide's line for `product-report.yml` names the second file. It is large, and the maintainers' size rule
    applies: it may be split in the brief (the structure and the markdown first, the file and the artifact after).
77. **The tests.** The recorded facts of the report goldens give one `report.json` each; a test renders the markdown from each and compares it with the golden markdown; a test validates each against
    `kit/report-schema.json`; a test builds a facts document with unknown values in every section; a test runs the script twice; the workflow file is read for rule 9; the inbox goldens are unchanged. No
    network and no model.

### From SPEC-0024: The report's cost totals count the merged changes whose hours are not known

Moved from SPEC-0024 by proposed spec amendments 108 (ADR-0244), the text of each rule unchanged. In this section a bare `rule N` means SPEC-0024 rule N, and SPEC-0024 rule N is rule N + 77 here; the tests, proof, residuals and rulings of these rules stay in SPEC-0024.

78. **The field.** The cost totals item of `report.json` (kind `week-totals`, SPEC-0022 rule 5) gains the field `hours_unknown`: a JSON integer, the number of the week's merged pull requests whose hours are `unknown` (the same condition that makes the `hours` of their `pull-request-cost` item and the `hours` of the totals read `unknown`: the created or the merged time is missing or cannot be read). It is present in every totals item and is 0 when every hours is known; it is never omitted, never a null and never the string `unknown`.
79. **The set counted.** It counts every pull request merged in the report's week, the set that `merged` counts, whether or not the per-change cost items are printed (a busy week leaves them out). So `merged` minus `hours_unknown` is the number of changes whose hours are in the total of `hours`; when `hours_unknown` is above 0 the total of `hours` is `unknown`, as before.
80. **Nothing printed changes.** The markdown report and the inbox output are byte-identical to before: the field is data only and the line "This week: ..." does not print it. The markdown rendered from `report.json` alone still equals the printed markdown (SPEC-0022 rule 2); the existing markdown and inbox goldens do not change.
81. **The schema number rises.** `report.json` `schema` is the number 2 for every report (SPEC-0022 rules 3 and 7: adding a field raises the number). `kit/report-schema.json` requires the number 2 and the field `hours_unknown` (an integer, at least 0) on the totals item, so a missing or an extra field fails. `facts.json` and its schema keep their own number 1. A reader that expects schema 1 sees the number change and knows to update.
82. **Unknown stays unknown.** When the facts do not hold the pull requests (SPEC-0022 rule 6) there is no totals item; the `unknown` item stands as before. A week with no merged pull request has no cost items, as before.
83. **Generic and deterministic.** The change adds no import and reads only the facts file; the same facts, day and week give a byte-identical `report.json` (SPEC-0022 rule 8).
84. **How it changes.** SPEC-0022 is Approved: the build changes it by `docs/runs/proposed-spec-amendments-N.md`, applied by its ADR: rules 3 (the number of the schema), 5 (the fields of `week-totals`) and 7 (`schema` is 2). The build is a kit change (a bump, the hashes, the plugin and `agk.toml` versions, an ADR that names the protected classes `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`), and the `report.json` goldens, which hold the number and the field, are regenerated with it. It is small.
85. **The tests.** The recorded facts of the report goldens, where some pull request has no time, give a count above 0 and the same facts with the times filled give 0; a busy week counts every merged pull request; every golden `report.json` validates against `kit/report-schema.json` with the number 2; a totals item without the field, with the string `unknown` or with an extra field fails the schema; the markdown and inbox goldens and the markdown rendered from `report.json` are unchanged. No network and no model.

### From SPEC-0026: Each section of the weekly report, each grouped item in it and each total that can be unknown states how many it holds

Moved from SPEC-0026 by proposed spec amendments 108 (ADR-0244), the text of each rule unchanged. In this section a bare `rule N` means SPEC-0026 rule N, and SPEC-0026 rule N is rule N + 85 here; the tests, proof, residuals and rulings of these rules stay in SPEC-0026.

86. **The section counts.** `report.json` (SPEC-0022 rule 3) gains the key `counts`: an object with exactly the keys `delivered`, `proven`, `needs_you` and `at_risk`, the keys of the sections, each counted by meaning and not by list entries: `delivered` is the number of its `requirement-done` items; `proven` the number of its `requirement-proven` items; `needs_you` the number of the items of all its groups together, `unknown` items excluded; `at_risk` the number of its items, `unknown` items excluded. The busy-week summary item of `delivered` and the `planned-not-counted` and `requirement-not-proven` items of `proven` are not counted, so the same requirements give the same `delivered` count in a quiet and in a busy week. An empty section is the integer 0. When a section holds an `unknown` item its count is the string `"unknown"`, never a number: unknown is not shown as a count. `counts` is always present and has these four keys. The `cost` section ("Time and review") has no count.
87. **The group counts.** Every grouped item, the kinds that list `entries` (`pull-requests-open-long`, `pull-requests-sent-back`, `pull-requests-merged-no-verdict`, `pull-requests-merged-not-cleared`), gains the field `count`: a JSON integer, the number of its `entries`, always present. The groups of the decisions section keep their `count` (a number or `"unknown"`, SPEC-0022 rule 3); the drift-audit item keeps its `total` and `counts` as they are.
88. **The unknown fix verdicts.** The `week-totals` item (SPEC-0022 rule 5) gains `fix_verdicts_unknown`: a JSON integer, the number of the week's merged pull requests whose verdicts are unknown, the same set as `merged` counts, whether or not the per-change cost items are printed. It is present in every totals item and is 0 when none is unknown; it is never omitted and never `"unknown"`. When it is above 0 the total `fix_verdicts` is `unknown`, as before.
89. **What stays not known yet.** A decisions group whose source cannot be read keeps `count` `"unknown"` and its single `unknown` item, and the drift-audit `total` stays a number or `"unknown"`: their items cannot be counted, so no unknown count is added for them and they are not turned into numbers.
90. **Open pull requests with unknown verdicts are not skipped.** Open pull requests whose verdicts cannot be read are no longer left out of the report. The pull-request group of the decisions section gains one `unknown` item, and so does the at-risk section, each naming in its `what` how many open pull requests could not be read, with a link to each of them (`links`, kind `pull-request`). When none is unreadable nothing is added. The `unknown` item has the fields it has (SPEC-0022 rule 5), so the number is in the text of `what`.
91. **The drift-audit line.** The `drift-audit` item of the at-risk section is present only when its `total` is above 0 or `"unknown"`; a total of 0 with no open drift-audit issue is left out (the section may then be empty and prints `nothing this week`). A total of 0 with an open issue stays listed, since the open issue is itself a thing to look at.
92. **The schema number rises and the markdown changes only where asked.** `report.json` `schema` is the number 3 for every report (SPEC-0022 rules 3 and 7: adding a field raises the number), the list of kinds is unchanged, and `kit/report-schema.json` requires the number 3, `counts`, and the new field of each kind, so a missing or an extra field fails. `facts.json` and its schema keep their own number. The markdown report and the inbox output change only by the unknown lines of rule 5 and the absent drift-audit line of rule 6; their goldens change only there, and the markdown rendered from `report.json` alone still equals the printed markdown (SPEC-0022 rule 2).
93. **Generic and deterministic.** The change adds no import and reads only the facts file; the same facts, day and week give a byte-identical `report.json` and markdown (SPEC-0022 rule 8).
94. **How it changes.** SPEC-0022 is Approved: the build changes it by `docs/runs/proposed-spec-amendments-N.md`, applied by its ADR: rules 3 (the key `counts`, the number of the schema), 5 (the fields) and 7 (`schema` is 3), and the rule that skipped open pull requests. The build is a kit change (a bump, the hashes, the plugin and `agk.toml` versions, an ADR that names the protected classes `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`), the goldens of `report.json` and of the markdown are regenerated with it, and it is measured first and split at about 600 changed lines of code and tests.
95. **The tests.** For every golden `report.json`: each number of `counts` equals the number of the items of its kind (rule 1), a busy and a quiet week give the same `delivered` count for the same requirements, a section with an `unknown` item gives `"unknown"`, each group `count` equals its entries and `fix_verdicts_unknown` equals the merged pull requests with unknown verdicts, and a test fails if any count differs from what it counts by meaning (rule 1) or a field is missing; a week with facts that could not read the pull requests keeps the `unknown` items and adds no count to them; open pull requests with unknown verdicts give the two `unknown` items with their links, and none give no item; a drift-audit total of 0 with and without an open issue, above 0 and unknown; every golden validates against the schema file with the number 3 and a missing or an extra field fails; the markdown goldens differ from before only in the lines of rules 5 and 6. No network and no model.

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

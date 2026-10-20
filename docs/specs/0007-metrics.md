# SPEC-0007: Per-PR metrics

- Status: Approved
- Owner: maintainers
- Requirements: REQ-012 (AC1)

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
The open points Q-K3-30 to Q-K3-36 were ruled on by the maintainers on 2026-10-15 (`docs/runs/spec-0007-notes.md`).
This spec is K3 criterion d of ADR-0015. REQ-012 AC1 reads "rejections, blocked weakenings, deviations,
cost class"; those four are the **core fields** below and the other fields are **supporting**; both are in scope and
the implementation's ADR amends REQ-012 (rule 19). GitHub response shapes marked `(verify)` were not read for this draft.

## Rules

### What is recorded

1. **A measurement, not a claim.** Every field is derived by a script from git and the GitHub REST API after the pull
   request is closed. No field is typed by an agent into the pull request body in K3: an agent-written number is a
   claim, a derived one is a measurement. `check_pr_body.py` is unchanged. The verdict lines of rule 4 are the one input a person's
   words supply, and they are relayed by the session (see the residual).
2. **One record per closed pull request.** The week's set is every pull request whose `closed_at` falls in the window
   of rule 12, merged or not. A record has `number`, `state` (`merged` or `closed`), `opened_at`, `closed_at`,
   `source` (always `derived`) and the fields of rules 3 to 9. Times are UTC, `YYYY-MM-DDTHH:MM:SSZ`.
3. **`hours_open_to_merge`** (supporting). `merged_at` minus `created_at` in hours, one decimal, round half up; empty
   for a closed pull request. Source: `pulls/N`.
4. **Verdict comments, and `rejected`** (core, "rejections"). Every reviewer verdict starts with one line, exactly one
   of `Verdict: cleared <short sha>`, `Verdict: fix list` or `Verdict: rejected`, and the implementation session posts
   that line verbatim as a pull request comment before it works on the verdict. A *verdict comment* is a comment
   (`issues/N/comments`, any author) whose first line is one of the three forms. `rejected` is `yes` when the pull
   request is `closed` without merge or has any `Verdict: rejected` comment, otherwise `no`; `rejected_verdicts` is the
   number of those comments. Source: `pulls/N`, `issues/N/comments`.
5. **`review_rounds`** (supporting). The number of `Verdict: fix list` comments. `unknown` when the pull request has
   no verdict comment at all. The `CHANGES_REQUESTED` review state and any reading of commits after comments are not
   used.
6. **`blocked_weakenings`** (core). The number of head commits of the pull request on which the check run named
   `governance` concluded `failure` and a step named by a check of the weakening set (rule 13) failed. The field counts
   law checks that blocked a head commit, including honest mistakes; it does not say a change was a weakening. Source:
   `commits/SHA/check-runs`, then the job's `steps` from `actions/jobs/ID` (the check run `id` equals the Actions job id, confirmed by a GET on 2026-10-15).
   `governance_failures` (supporting) counts head commits where `governance` failed for any step.
7. **`deviations`** (core). The number of files the pull request adds under `docs/runs/` named
   `proposed-spec-amendments-*.md` (SPEC-0001 to SPEC-0005 practice, `check_specs` rule). Source: `pulls/N/files`
   (`status` `added`). A pull request that departs from an Approved spec without that file is not counted here; that is
   what a human review is for.
8. **Supporting fields, from the files and the git history.**
   - `protected_classes`: the sorted class names of `config/protected-paths.txt` at the parent of the merge commit (merged) or at the pull request's base commit (closed) that any path in
     `pulls/N/files` matches (substring match, as `check_protected_changes`). Empty when none.
   - `adrs_added`: the count of added files matching `docs/adr/NNNN-*.md`.
   - `size`: `additions`, `deletions`, `changed_files` from `pulls/N`.
   - `actual_hours`: for a merged pull request, `merged_at` minus the earliest author date among the commits of `pulls/N/commits`, in hours, one decimal, round half up; `none` for a closed pull request; `unknown` when a commit date is missing or unreadable (SPEC-0018 rule 3).
   - `estimated_size`, `estimated_hours`: read from the pull request body of `pulls/N`: the lines `Size: S|M|L` and `Expected: <low>-<high> hours`; both `unknown` when either line is missing, repeated or malformed (SPEC-0018 rules 2 and 3).
   - `tests_before`, `tests_after`: for a merged pull request, the number of lines matching `^\s*def test_` in the files
     under the `test_dirs` of `agk.toml` (default `["tests"]`) at `merge_commit_sha^` and at `merge_commit_sha`
     (a squash merge has one parent). It is a static count: parametrized cases are not expanded and the tests are not
     run. Source: local git objects of the default branch; empty for a closed pull request.
   - `merged_head_cleared`: `yes` when a `Verdict: cleared <sha>` comment names the merged head commit (the sha is a
     prefix of the head); `no` when the last verdict comment names another commit or is not `cleared`; `unknown` when
     there is no verdict comment.
9. **`cost_class`** (core): the maintainers' review cost, derived and never typed. `S`: `review_rounds` is 0 and
   `hours_open_to_merge` is under 24. `M`: `review_rounds` is at most 2 and `hours_open_to_merge` is under 72. `L`:
   anything else, and any pull request closed unmerged. `unknown` when `review_rounds` is `unknown` (a closed
   unmerged pull request is `L` regardless).
10. **No inference.** A field whose inputs are missing is `unknown`, never `0` or `no`. The weekly body counts the
    `unknown` values per field.

### The weekly aggregation: one place

11. **Its own run, and the issue is the record.** The aggregation is not part of the drift audit. A script
    `scripts/agk/metrics.py` and a workflow `.github/workflows/metrics.yml` (Monday, `43 6 * * 1`, and
    `workflow_dispatch` with an optional `today`) produce **one issue per ISO week** titled `agk metrics YYYY-Www`,
    labelled `agk-metrics`, whose body is the report. It is the only place the weekly numbers are written. Reasons, in
    `docs/runs/spec-0007-notes.md`: SPEC-0004 rule 14 (a clean drift run writes nothing) cannot give two weeks of
    evidence; a file committed by the workflow would need a pull request, and the ruleset allows no bypass.
12. **The window.** `--today YYYY-MM-DD` (default `date -u`) names the run day. The window is the full ISO week before
    the week of `--today`: Monday 00:00:00 UTC to the next Monday 00:00:00 UTC (half-open). The week label is the
    ISO week of the window's Monday. Two runs with the same `--today` and the same input give byte-identical output.
13. **The weakening set.** The checks whose failure counts as a blocked weakening: `check_protected_changes`,
    `check_requirements`, `check_adrs`, `check_specs`, `reviewers --check-codeowners` and `check_kit_tests`.
    `check_neutrality` and `check_build_state` are not in it. The implementation splits `governance.yml` into one step
    per check, each named by its check id; the job, and so the required check `governance`, is unchanged. Until that
    split is merged, `blocked_weakenings` is `unknown` for every pull request, and `governance_failures` is still counted.
14. **Body shape.** The first line is `agk metrics YYYY-Www (window YYYY-MM-DD to YYYY-MM-DD)`, then a table with one
    row per record sorted by `number`, with the fields of rules 2 to 9 as columns, then a totals line per core field,
    then `closed in window: N; recorded: N; unknown cells: N`, then the note "Derived from git and the GitHub REST
    API; no field is typed by an agent." and the final line `<!-- agk-metrics YYYY-Www -->`. A line before the header carries a flag (rules 15 and 16: `duplicate metrics issues: ...`, then `INCOMPLETE: ...`); a clean body
    starts with the header. A week with no closed
    pull request is still written, with `closed in window: 0` (the issue is the evidence that the run happened).
15. **One issue per week.** A pure function `choose_action(open_and_closed_issues, week)` returns `create` or
    `update N` (never `none`): the issue with the marker of that week is updated by replacing its body. More than one
    issue with the same marker is reported on the first line of the body as `duplicate metrics issues` and the
    lowest-numbered issue is updated. The script takes `--issues FILE` (JSON of issues with `number`, `title`, `body`),
    `--print-action`, `--print-title` and `--print-body` (the default mode), and `--repo OWNER/REPO` for live runs
    (default: `GITHUB_REPOSITORY`, then the URL of `origin`) and `--api-dir DIR` to read recorded responses.
16. **Completeness is measured twice.** The script lists the closed pull requests of the window by `pulls?state=closed`
    (sorted by update, paged until `closed_at` is before the window) and counts `closed in window` from that list; it
    then fetches the details of each and counts `recorded`. A difference is printed on the first line as
    `INCOMPLETE` and the exit code is 1.
17. **Read-only on the repository.** The script reads with `gh api` `GET` only, writes only to stdout, and holds no
    credential (as SPEC-0006 rule 2). The workflow's
    permissions are `contents: read`, `pull-requests: read`, `checks: read`, `actions: read` and `issues: write`; its
    only write calls are `gh issue create`, `gh issue edit` and creating the label if missing. The checkout has
    `fetch-depth: 0` for rule 8. The `today` input of `workflow_dispatch` reaches the shell through an environment
    variable (`INPUT_TODAY`), never interpolated into the script text.
18. **Pinned actions.** The workflow's `uses:` lines are pinned to full commit SHAs with the tag in a comment.
19. **Files and ownership.** The workflow (`.github/`), the script (`scripts/agk/`), its tests (`tests/kit/`) and the
    manifest (`kit/`), the wiring tests (`tests/kit_dev/`) and the requirements text (`docs/requirements.md`) are protected classes; the implementation PR carries an ADR naming each, and an ADR that amends
    REQ-012's acceptance text (the proposed text is in the notes). Init and adopt install the workflow by
    default, as for the drift audit (SPEC-0004 rule 16), and print that it needs `issues: write`. The ADR also states
    the cost class definition of rule 9 in REQ-012's text.

### Tests and proof

20. **Fixtures, no network, no model.** `tests/kit/fixtures/metrics/<case>/` holds responses in the shape of the recorded ones, as JSON
    (`pulls.json`, `pull-N.json`, `reviews-N.json`, `comments-N.json`, `commits-N.json`, `files-N.json`,
    `checks-SHA.json`, `jobs-ID.json`) and `issues.json`, with the author names replaced. The test count of rule 8 is
    tested on a git repository built in `tmp_path` with dated commits. Cases: a merged pull request with no verdict
    comment; one with two `Verdict: fix list` comments and a `Verdict: cleared` naming the head; one whose last verdict
    names another commit; one with `Verdict: rejected`; one whose verdict lines carry trailing text (not verdicts); one closed unmerged; each cost class `S`, `M`, `L` and
    `unknown`; one that adds an ADR; one that touches two protected classes; one
    that adds a `proposed-spec-amendments` file; a failed `governance` run; a week with no closed pull request; a
    week that spans a month and a year boundary; and a pull request closed at exactly the window's start and end.
21. **Determinism.** The same fixture and `--today` give byte-identical bodies; a different `--today` in the same week
    gives the same body; the fixtures include records in shuffled order and the output is sorted.
22. **Action.** `choose_action` is tested for: no issue (create), one issue (update N), two issues with the same marker
    (update the lowest, report the duplicate), an issue of another week (create).
23. **Unknown stays unknown.** A fixture with a pull request missing its reviews file yields `unknown`, not `no`, and
    the count of unknown cells in the totals line.
24. **Proof (criterion d of ADR-0015).** After the workflow is installed on `gbvraju/agk`, the issues `agk metrics
    YYYY-Www` and `agk metrics YYYY-W(ww+1)` exist for two consecutive ISO weeks, each created by the workflow, each
    with `closed in window` equal to `recorded` and equal to the count the maintainers read from the pull request
    list for the same window by hand. The two issue numbers and the comparison are recorded in `docs/runs/`. A week
    that the schedule missed is run by `workflow_dispatch` with `today`; the issue says it was run by hand, and a
    week run by hand does not count towards the two consecutive scheduled weeks unless the maintainers accept it.

## Tests

- Rules 1-10, 20, 23: `tests/kit/test_metrics.py`, marker `REQ-012 AC1`.
- Rules 11-16, 21, 22: the same file, marker `REQ-012 AC1`.
- Rules 17, 18: `tests/kit/test_metrics_workflow.py` (permissions, pinned actions, the only write calls), marker `REQ-012 AC1`.
- Rule 24: a record in `docs/runs/`, checked by the maintainers, not by a test.

## Residual

- 2026-10-15: the verdict line is relayed by the implementation session from the same account that opens the pull
  request, so it is a relayed record, not a signed one; the maintainers check it at merge (due 2026-12-31).
- 2026-10-15: `blocked_weakenings` is `unknown` until `governance.yml` is split into one step per check; the first weeks
  may carry `unknown` (due 2026-11-15).
- 2026-10-15: the weekly record lives in a GitHub issue, which a repository admin can edit or delete; the numbers can be
  recomputed with the script and `--today` (due 2026-12-31).

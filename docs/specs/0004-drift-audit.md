# SPEC-0004: Drift audit

- Status: Approved
- Owner: maintainers
- Requirements: REQ-011

Status is `Draft` or `Approved`. An Approved spec is owned by its reviewer group; agents propose patches.
The open points Q-ON-13 to Q-ON-19 were ruled on by the maintainers on 2026-10-15 (`docs/runs/spec-0004-notes.md`);
Q-ON-18 (the schedule time) stays open.

REQ-011 (drift audit): AC1 weekly; AC2 one issue per run; AC3 read-only. Rules map to them below.

## Rules

### Purpose and boundaries

1. **Purpose.** The audit finds what the per-PR checks could not see: changes that reached the default branch without
   passing them (a direct push, an administrator bypass), and drift that builds up with time (stale drafts, overdue
   residuals, reviewers and CODEOWNERS out of step). It reports; it fixes nothing (principle 2).
2. **Read-only (AC3).** The audit never writes a file, a branch, a commit, a comment on a pull request, a label other
   than its own, or any other issue. Its only write is the one issue of rule 13. Its workflow has
   `permissions: contents: read` and `issues: write` and nothing else.
3. **Deterministic first.** Findings come from a stdlib script, `scripts/agk/drift_audit.py`, that reads git history
   and repository files only: no network, no `gh`, no model. An optional model summary (the existing read-only
   `drift-auditor` agent over the script's report) is deferred to K3 and off by default.

### Schedule

4. **Weekly, default branch only (AC1).** A workflow `.github/workflows/drift-audit.yml` runs on a cron schedule once a
   week (draft: Saturday 06:17 UTC, a minute that is not on the hour) and on `workflow_dispatch`, never on
   `pull_request` or `push`. Scheduled workflows run from the default branch; the job also checks
   `github.ref_name == github.event.repository.default_branch`. It checks out the default branch with full history.
   The workflow keeps `workflow_dispatch` so maintainers can run it by hand. Rule 23 covers scheduled workflows being
   disabled.
5. **The window.** "The last 7 days" is `--since` the run date minus 7 days, computed from the date given to the script
   (`--today YYYY-MM-DD`, default the UTC clock), so tests are reproducible.

### Scope: what it checks

6. **D1 protected change without an ADR.** For each first-parent commit on the default branch in the window that
   touches a path of `config/protected-paths.txt`: the commit must add or modify a `docs/adr/*.md` (not
   `TEMPLATE.md`, not a Status-only edit) whose text names every touched protected class, exactly the rule of
   `check_protected_changes`, applied per commit. The protected list used is the one at the commit's parent. A commit
   that fails yields one finding per touched protected class that no single ADR of the commit covers together, as
   the per-PR check prints one failure per class (the subject is the first 12 characters of the commit id, then the
   protected class, never content). The Status-only exemption for `docs/requirements.md` applies as in the check.
7. **D2 done requirements without markers.** At the head of the default branch, every requirement with
   `- Status: done` has a marker in the configured test directories and patterns (the logic of
   `check_requirements`). D2, D4 and D5 read the work tree and D1 and D3 read the history of the default branch, so
   the audit is meant to run on a checkout of the default branch, as the workflow does.
8. **D3 stale drafts.** A spec with `Status: Draft` older than N days and an ADR with `Status: Proposed` older than N
   days (N = 14). The age of an ADR is its `Date:` field; the age of a spec is the date of the commit
   that added the file (`git log --diff-filter=A`), because specs carry no date.
9. **D4 overdue residuals.** A `## Residual` bullet of an ADR or spec that carries `(due YYYY-MM-DD)` with a date before
   the run date. Residual bullets without a due date are counted in the report but are not findings. The convention
   is `(due YYYY-MM-DD)` at the end of the bullet. D4 also reads `docs/runs/residuals.md`: each line of its `## Open`
   section has the form `- <source> | <text> | (due YYYY-MM-DD) | <status>`; a line whose date is before the run date
   is a finding naming its source. A bullet in a new ADR or spec carries its own `(due YYYY-MM-DD)`; the register
   exists for bullets of Accepted ADRs and Approved specs, which cannot change. A malformed line in the `## Open`
   section is reported as a finding, not skipped. A bullet that a row of the register's `## Closed` table names is not a finding: the row's first
   cell is the bullet's source and its second cell is the bullet's text without the leading `YYYY-MM-DD: ` and the trailing `(due YYYY-MM-DD)`, or the
   whole bullet text (whitespace collapsed, otherwise an exact match; a different text, source or case does not close it). The subject of an overdue ADR or spec bullet is the file path, of
   an overdue register line its source field, of a malformed register line `docs/runs/residuals.md:LINE`; only
   bullet lines (`- `) of the `## Open` section are register entries.
10. **D5 reviewers and CODEOWNERS drift.** The committed `.github/CODEOWNERS` equals the rendering of
    `config/reviewers.yaml` (or its marked block in an adopted repository); the `protected` class equals
    `config/protected-paths.txt`; a team handle is still the placeholder `@REPLACE-ME` (an `agk doctor` residual of
    SPEC-0001).
11. **Findings shape.** Each finding has a code (`D1`..`D6`), a subject (a commit id, a path or a requirement id), a
    rule or ADR it breaks, and one sentence. No finding quotes file content or a setting value (principle 8). The
    report starts with a summary line (date, window, counts per code), then the findings sorted by code and subject.
12. **Nothing else.** The audit does not check what a PR check already guarantees at merge time except as D1-D2
    re-checks of the default branch; style, tests and lint are out of scope.

### Output

13. **Exactly one issue per run (AC2).** A run that has findings creates one issue, or updates the one open issue
    carrying the label `agk-drift-audit` by replacing its body; it never opens a second one. Its title is
    `agk drift audit YYYY-MM-DD` (updated on each run). The body is the report; its last text line is the note of
    rule 23 and its final line is the marker `<!-- agk-drift-audit -->`. The workflow's only write calls are
    `gh issue create` and `gh issue edit` for that issue (and creating the label if it is missing); it also reads
    with `gh issue list` to find the open audit issue.
14. **Clean runs.** A run with no findings writes nothing, whether or not an audit issue is open, and prints a
    one-line summary to the job log. An open audit issue is left for maintainers to close. The audit never closes an
    issue.
15. **Selecting the issue.** A pure function `choose_action(open_issues, has_findings)` returns `create`, `update N` or
    `none` (always `none` when there are no findings); more than one open audit issue is itself reported in the
    body as finding D6 (`duplicate audit issues`) and the lowest-numbered issue is the one updated. So that the
    decision stays in the tested script, `drift_audit.py` takes `--open-issues 'N N'` (the numbers of the open
    audit issues, used for D6 and for the action), `--print-action` (`create`, `update N` or `none`),
    `--print-title` (`agk drift audit YYYY-MM-DD`) and `--branch NAME` (the default branch; default from
    `agk.toml`).

### Install

16. **Files and ownership.** The workflow (`.github/`), the script (`scripts/agk/`), its tests (`tests/kit/`) and the
    manifest (`kit/`) are protected classes: the implementation PR carries an ADR naming each. Whether init and adopt
    install the workflow by default (it needs only the `GITHUB_TOKEN`, no secret); a project can remove it.
17. **Pinned actions.** The workflow's `uses:` lines are pinned to full commit SHAs with the tag in a comment, as the
    governance workflow's are.

### Proof

18. **Fixture repositories with known drift.** Built in `tmp_path` with dated commits (author and committer dates set):
    a direct commit touching `.claude/settings.json` without an ADR 3 days ago (D1: found), the same 20 days ago
    (outside the window: not found), the same with an ADR naming `.claude/` in the same commit (not found); a
    `done` requirement without a marker (D2); a Draft spec added 30 days ago and a Proposed ADR dated 20 days ago
    (D3); an ADR residual `(due 2026-01-01)` (D4); a register line past its date (found), one in the future (not
    found) and a malformed one (found) (D4); a CODEOWNERS edited by hand, and a placeholder team (D5); a clean
    repository (no findings).
19. **Script tests.** The same repository and `--today` give byte-identical reports; the report order is stable; the
    script writes nothing (a before/after snapshot) and has no network or process imports beyond `git`; the window
    boundary day is tested on both sides.
20. **Issue selection tests.** `choose_action` for: no open issue with findings (`create`), one open issue
    (`update`), two open issues (`update` the lowest and report the duplicate), none with no findings (`none`), one
    open issue with no findings (`none`).
21. **Workflow shape tests.** A test reads `.github/workflows/drift-audit.yml`: triggers are only `schedule` and
    `workflow_dispatch`; one weekly cron; `permissions` is exactly `contents: read` and `issues: write`; every `uses:`
    is a 40-character SHA; the only `gh` verbs are `issue list` (read-only), `issue create` and `issue edit`
    (and `label create`); no `git push`, no `gh pr`, no `gh issue close`, no `gh issue comment`.
22. **No network in tests.** Tests use no network and no model. The live behaviour on GitHub (cron, label, issue) is
    proven once by hand on a repository maintainers choose, recorded in `docs/runs/`.
23. **Scheduled workflows may be disabled.** GitHub may disable scheduled workflows in a repository after a period of
    inactivity (the period is (verify) against current GitHub documentation). The audit documents this in a comment
    at the top of `drift-audit.yml` and in the installed documentation, and reports it: the body of every audit
    issue has, as its last text line before the marker, a line saying that scheduled runs can stop after
    repository inactivity and that `workflow_dispatch` runs the audit by hand. A test checks that the workflow carries the comment and that the
    report ends with the line.

## Tests

- Rules 5-12, 18-19: `tests/kit/test_drift_audit.py` and `tests/kit/drift_fixtures.py`, marker `REQ-011 AC1`.
- Rules 13-15, 20: `tests/kit/test_drift_audit.py`, marker `REQ-011 AC2`.
- Rules 2, 17, 21, 23 (comment): `tests/kit/test_drift_workflow.py`, marker `REQ-011 AC3`.
- Rules 11-12, 23 (report line): `tests/kit/test_drift_audit.py`, marker `REQ-011 AC1`.
- Rule 22: the one live run, recorded in `docs/runs/`.

## Residual

- 2026-10-14: the model summary is not in this spec's first implementation.
- 2026-10-14: scheduled-workflow behaviour (jitter, the period after which GitHub may disable schedules) is (verify)
  against current GitHub documentation (rule 23).
- 2026-10-14: residual due dates need the convention of rule 9 and a backfill PR before D4 finds anything.

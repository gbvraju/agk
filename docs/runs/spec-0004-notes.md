# Notes on SPEC-0004 (drift audit)

Date: 2026-10-14 (from `date -u`). Overnight item D. The spec is a Draft for REQ-011; nothing is implemented.

## Decisions taken in the draft (each is a numbered rule)

- A deterministic stdlib script reads git history and files; the workflow only turns its report into one issue. No
  model, no network in the script (rules 3, 13).
- Weekly cron on the default branch, plus manual dispatch; never on PR or push events (rule 4).
- D1 reuses the rule of `check_protected_changes` per first-parent commit in the last 7 days, so it catches what the PR
  check never saw: direct pushes and administrator bypasses (rule 6). Finding the 7-day window from a `--today`
  argument keeps tests reproducible (rule 5).
- D2 re-checks `done` requirements against markers on the default branch head; D3 flags old drafts and Proposed ADRs; D4
  flags residuals that carry an explicit due date; D5 flags CODEOWNERS and reviewers drift and the placeholder team
  (rules 7-10).
- Exactly one issue per run: create, or replace the body of the single open audit issue; never close; clean runs write
  nothing unless an issue is open (rules 13-15).
- Permissions are `contents: read` and `issues: write` only, checked by a workflow-shape test that also forbids
  `git push`, `gh pr`, `gh issue close` and `gh issue comment` (rules 2, 21).

## Alternatives considered

- **One issue per finding.** Rejected: floods the tracker and breaks "one issue per run".
- **A new issue each run.** Rejected by REQ-011 AC2's intent (no duplicates); updating the open one gives a stable
  place to look.
- **Writing the report to a file on a branch.** Rejected: the audit is read-only (REQ-011 AC3) and generated files are
  not committed (principle 5).
- **A model-written summary in the first version.** Deferred: it needs a secret and cost approval; the deterministic
  report is the substance.
- **Counting residuals without due dates as findings.** Rejected: today's residual bullets record when a point was
  written (`- 2026-10-14: ...`), not when it is due; flagging all of them would be noise.

## Fixture matrix (rule 18)

| Fixture | Drift built in | Code | Expected |
| --- | --- | --- | --- |
| a direct commit touching `.claude/settings.json`, no ADR, 3 days ago | protected change without an ADR | D1 | found |
| the same commit 20 days ago | outside the 7-day window | D1 | not found |
| the same commit with an ADR naming `.claude/` in the same commit | covered | D1 | not found |
| a `done` requirement with no marker | done without a test | D2 | found |
| a Draft spec added 30 days ago; a Proposed ADR dated 20 days ago | stale drafts (N = 14) | D3 | found |
| a residual `(due 2026-01-01)` | overdue residual | D4 | found |
| CODEOWNERS edited by hand; the placeholder team still present | reviewers drift | D5 | found |
| two open audit issues (selection test only) | duplicate issues | D6 | lowest updated, duplicate reported |
| a clean repository | none | none | no findings |

## Rulings (maintainers, 2026-10-15)

Applied in the final commit of this PR, with a `workflow_dispatch` trigger (already in rule 4, now explicit) and a
rule on disabled schedules (23) added on the maintainers' instruction, and the status set to Approved.

| Question | Ruling | Where |
| --- | --- | --- |
| Q-ON-13 | N = 14 days | rule 8 |
| Q-ON-14 | `(due YYYY-MM-DD)` convention plus a later backfill | rule 9 |
| Q-ON-15 | a clean run writes nothing; an open issue is also left untouched (my reading) | rules 14, 15, 20 |
| Q-ON-16 | install by default | rule 16 |
| Q-ON-17 | model summary at K3 | rule 3 |
| Q-ON-18 | open: the schedule time (a placeholder); the inactivity period is (verify) | rules 4, 23 |
| Q-ON-19 | accepted; the run may create the label | rule 13 |

## Questions for maintainers

- **Q-ON-13:** the staleness limit N for Draft specs and Proposed ADRs (draft: 14 days each).
- **Q-ON-14:** a due-date convention for residuals, `(due YYYY-MM-DD)` at the end of the bullet (draft), and whether to
  backfill existing residuals; without it D4 finds nothing.
- **Q-ON-15:** a clean run with no open issue writes nothing (draft). The alternative is a weekly "no findings" issue,
  which is noisier but proves the job ran.
- **Q-ON-16:** install the workflow by default in init and adopt (it needs only the `GITHUB_TOKEN`), or behind a flag?
  The workflow needs `issues: write`, which a maintainers' repository setting may restrict.
- **Q-ON-17:** a model summary later through the existing read-only `drift-auditor` agent: wanted, and with what cost
  limit?
- **Q-ON-18:** schedule: Saturday 06:17 UTC is a placeholder. Also verify whether GitHub disables scheduled workflows
  after a period of repository inactivity and whether the schedule can drift by minutes (both (verify)); if it can be
  disabled, the audit should be documented as needing a periodic manual dispatch.
- **Q-ON-19:** the issue title (`agk drift audit YYYY-MM-DD`), the label name (`agk-drift-audit`), and whether the run may
  create the label if missing.

## Facts to verify before the spec is Approved

- GitHub scheduled-workflow semantics (default-branch only, delay, disabling on inactivity).
- `gh issue create`, `gh issue edit` and `gh label create` available on the hosted runner with the `GITHUB_TOKEN` and the
  permissions of rule 2.

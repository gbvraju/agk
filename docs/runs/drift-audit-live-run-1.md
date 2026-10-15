# Drift audit, live run 1 (SPEC-0004 rule 22)

Date: 2026-10-15 (from `date -u`). The one live run of the drift audit on GitHub, started by the maintainers with
`workflow_dispatch` on this repository after PR #23 merged. The facts below were read from the repository's Actions
API (read-only) by the session that wrote this record; the maintainers started the run.

| Item | Value |
| --- | --- |
| Workflow | `.github/workflows/drift-audit.yml` (`drift-audit`) |
| Run | 38722457104 |
| Event | `workflow_dispatch` |
| Commit | 60ac2b4 (the merge of #23, kit 0.6.0) |
| Created | 2026-10-15T10:44:58Z |
| Status and conclusion | completed, success |
| Job `drift-audit` | success, 10:45:01Z to 10:45:06Z |
| Steps | set up job, `actions/checkout`, "Audit and file at most one issue", post-run checkout, complete job: all success |

## What it shows

- The workflow runs, the pinned checkout works with full history, and the audit step ends with success on GitHub.
- No issue carries the label `agk-drift-audit` (read through the issues API after the run, state `all`). That is what a
  clean run produces (SPEC-0004 rule 14): no findings, so nothing written, no label created.
- The audit run against this repository's history on the same date by the session that built it also reported no
  findings (summary line `findings=0`).

## What it does not show

- It did not exercise issue creation, the issue update or the label creation, because there was nothing to report.
  Whether the workflow token may create the label (the register line "workflow token label creation (verify on first
  live run)", due 2026-10-22) is still open until a run has findings.
- The log text of the audit step was not read; only the conclusions of the job and its steps were.
- The period after which GitHub disables scheduled workflows is still (verify).

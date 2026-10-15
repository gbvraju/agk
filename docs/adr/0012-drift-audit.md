# ADR-0012: Drift audit (SPEC-0004)

- Status: Accepted
- Date: 2026-10-15
- Deciders: maintainers
- Related: ADR-0003, ADR-0010, ADR-0011
- Requirements: REQ-011

## Context

SPEC-0004 (Approved, with amendments 5) describes a weekly, read-only audit of the default branch: what reached it
without passing the per-PR checks, and drift that builds up with time. This PR implements rules 1 to 21 and 23; rule
22 (the one live run on GitHub) is a maintainers' step after merge. Deviations from the Approved spec were proposed in
`docs/runs/proposed-spec-amendments-8.md` and applied on the maintainers' instruction in this PR.

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`. This PR changes all five.

## Decision

1. **Script.** `scripts/agk/drift_audit.py [--today YYYY-MM-DD] [--branch NAME] [--open-issues 'N N']
   [--print-action | --print-title]` reads git history and repository files only (standard library, no network,
   no `gh`, no model, no writes) and prints one report: a summary line (date, window, counts per code), the count of
   residual bullets without a due date, the findings sorted by code and subject, a note that scheduled runs can stop
   after repository inactivity, and the marker `<!-- agk-drift-audit -->` as the last line.
2. **Checks.** D1 per first-parent commit of the default branch inside the window (the run date minus 7 days up to the
   run date, by UTC commit date): the commit's touched protected classes, taken from the list at its parent, must all
   be named by one ADR added or modified in the same commit (not a Status-only edit; the Status-only exemption for
   `docs/requirements.md` applies); otherwise one finding per class. D2 a `done` requirement without a marker at the
   head. D3 a Draft spec (age from the commit that added it) or a Proposed ADR (its `Date:`) older than 14 days. D4 an
   overdue `(due YYYY-MM-DD)` residual bullet of an ADR or spec, and the lines of `docs/runs/residuals.md` (`## Open`:
   `- <source> | <text> | (due YYYY-MM-DD) | <status>`; a malformed bullet line is a finding). D5 CODEOWNERS, the
   `protected` class and the placeholder team, using `reviewers.py`. D6 more than one open audit issue.
3. **The issue.** `choose_action(open_issues, has_findings)` is a pure function: `none` without findings, else
   `create` or `update N` for the lowest-numbered open issue. `--print-action` and `--print-title` give the action
   and the title from the same inputs, so the workflow holds no decision.
4. **Workflow.** `.github/workflows/drift-audit.yml`: cron `17 6 * * 6` (Saturday 06:17 UTC) and
   `workflow_dispatch`; `permissions` exactly `contents: read` and `issues: write`; one pinned action (checkout, full
   history); the job runs only on the default branch; the token is the workflow token. Its `gh` calls are
   `issue list` (read, to find the open audit issue), `issue create`, `issue edit` and `label create`. A comment at
   the top says GitHub may disable scheduled workflows after inactivity (the period is (verify)).
5. **Install.** The workflow, the script and the tests are in the manifest's verbatim set, so init and adopt install
   them; a project can remove the workflow. The tests are in `tests/kit/` (installed), as for SPEC-0003; the kit-only
   wiring tests are in `tests/kit_dev/test_drift_wiring.py`.
6. **Kit version** `0.6.0`: installed content changed. REQ-011 stays `planned`; an agent does not mark it done. The
   reviewer wiring test that pinned version 0.5.0 now asks for at least 0.5.0 (`tests/kit_dev/test_reviewer_wiring.py`).

## Consequences

- A weekly issue lists what slipped past the per-PR checks; a clean week writes nothing.
- Installed repositories gain a workflow that needs `issues: write`; a repository setting may restrict that.
- The audit reads the work tree for D2, D4 and D5, so it is meant to run on a checkout of the default branch.
- The first scheduled run happens by itself after merge; the live check of rule 22 is a maintainers' step.

## Residual

- 2026-10-15: whether the workflow token may create labels, and when GitHub disables scheduled workflows, are
  unconfirmed (verify) (due 2026-11-15).
- 2026-10-15: the model summary is deferred (SPEC-0004 rule 3) (due 2027-01-31).
- 2026-10-15: class naming in an ADR is still a substring match (ADR-0003 residual).

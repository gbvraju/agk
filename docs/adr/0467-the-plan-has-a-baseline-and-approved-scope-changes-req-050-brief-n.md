# ADR-0467: The plan has a baseline and approved scope changes

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, ADR-0269, ADR-0454, ADR-0465, ADR-0466, `Q-S0043-7`, brief #1095, brief #1094, plan #661
- Requirements: REQ-050

## Context

SPEC-0043 (Approved, REQ-050, ADR-0269) rules 20 to 22 make the confirmed plan a baseline that never changes and make
a change of scope a record the person approves before its briefs are added. On the default branch at 2c6cd40
`plan_status.py` (build (f), ADR-0466) already reads `docs/plan/scope-changes.md` and the presence of
`docs/plan/baseline.json`, but nothing checks either file, `plan_estimate.py` (build (e), ADR-0465) prints no effect
of a change, and `scripts/agk/reviewers.py` reads no `Approve: scope` line. This is build (g) of rule 27.

## Decision

1. `docs/plan/baseline.json` is one JSON object with exactly the fields of rule 20: `schema` 1, `head` (the full
   confirmed head ID), `date` (`YYYY-MM-DD`), `link` (an `https://` address of the `Approve: plan` comment) and
   `milestones`, a list whose items hold exactly `id` (`M<n>`), `briefs` (the brief keys, each once), `target` (a
   real date or null) and `estimate` (the text printed then). `check_plan.py` fails another shape naming the field,
   or `milestones[<n>]`, never a value.
2. The baseline is never rewritten (rule 20, as `check_build_state.py` for principle 4): `check_plan.py` reads, with
   git, the file at the merge base with `--base REF` (else `AGK_BASE`, `GITHUB_BASE_REF` or the default branch, the
   order of `common.resolve_base`), and fails a baseline the merge base holds that the working tree changed or
   removed. A base that does not resolve in CI is a failure (`common.resolve_base` raises and `run` prints it, as in
   the other checks that read a base); only outside CI with no base, or with a root outside any git work tree (no
   history to compare), is the comparison not made, and the shape is still checked.
3. A scope change is one block of `docs/plan/scope-changes.md` that starts `Scope change: SC-<n>` and holds the lines
   `What:`, `Why:`, `Source:` (a location of rule 1, or `person <date>`), `Effect:` and `Status: proposed`
   (rule 21), the shape `plan_status.py` already reads. The briefs it adds and removes are named on one more line,
   `Briefs: +M<n>/<key> <size> <low>-<high> hours; -M<n>/<key>`, so the check and the estimate read them without
   parsing prose; a block without it changes no brief (a moved target date). A missing line, a status other than
   `proposed`, a number used twice and an entry of another shape fail, naming the rule and the number.
4. A scope change is approved by its `Approved: <date> <https link>` line, which the session appends after the
   person's `Approve: scope SC-<n> <full head ID>` (rule 22). With `--comments FILE`, the saved comments of the pull
   request, the line counts only when an account of `spec_approvers` gave that approval, never through an app of
   `agent_apps` and, in solo mode, inside the person's whole `Confirmed:` comment (`Q-S0043-7`):
   `reviewers.APPROVE_SCOPE` and `reviewers.scope_approvals`, and `reviewers.confirmed_comments` carries the line as
   it carries `Approve: plan`. A session never posts the line.
5. Rule 22: `check_plan.py` fails a brief file whose `Milestone:` is a milestone of the baseline and whose key is
   neither in that milestone's `briefs` nor added there by an approved scope change, and a baseline brief no longer
   under its milestone that no approved scope change removes, each naming the key and the milestone. A milestone
   the baseline does not hold is not controlled.
6. `plan_estimate.py --with SC-<n>` prints `effect of SC-<n>: before`, the estimate without the change, then
   `effect of SC-<n>: after`, the estimate with it (each milestone with its `inputs:` line), and the limits line once;
   the person copies the hours and dates into `Effect:`. An added brief counts after the change from its entry (its
   file, if it already exists, is left out before); a removed brief file is left out after it. Briefs read from the
   facts carry no key, so a removal changes only brief files. An unknown or malformed `SC-<n>` exits 2 naming
   `--with`.

Protected path classes changed: `scripts/agk/` (`check_plan.py`, `plan_estimate.py`, `reviewers.py`), `tests/kit/`
(`test_check_plan_scope.py`, new), and `agk.toml` (the new test file in three
`[[testing.map]]` entries). `kit/hashes.json` does not change: `kit_hashes.py` prints `ok kit-hashes`.

## Consequences

Once the person confirms a plan, the briefs under its milestones change only with a recorded, approved scope change
whose effect on the estimate was printed; the baseline stays as confirmed. A project without a baseline sees no
change.

## Residual

- 2026-11-12: without `--comments` (the governance run) an `Approved:` line is read as written; the account behind it
  is checked only where the saved comments are given (due 2027-01-31).
- 2026-11-12: a moved `Target:` is recorded by a scope change but not checked against the baseline, and the report
  does not yet show the baseline and the current plan side by side (rule 20's last clause) (due 2027-01-31).
- 2026-11-12: rule 20's "a commit that changes only that file" for the first write is not checked (due 2027-01-31).

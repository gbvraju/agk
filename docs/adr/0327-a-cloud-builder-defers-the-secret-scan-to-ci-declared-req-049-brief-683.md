# ADR-0327: A cloud builder defers the secret scan to CI, declared in the body (REQ-049, brief 683)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0306, ADR-0158, SPEC-0039, SPEC-0042
- Requirements: REQ-049

Protected classes: `scripts/agk/`, `config/`, `tests/kit/`

## Context

ADR-0306 (brief #632, merged as #640) made the secret scan mandatory in every mode: `prepush.py`
fails when `gitleaks` is not on `PATH`, and session rule 31 lets a push follow only a passing
prepush. The same day, every cloud builder session was refused the gitleaks download by both
routes it has (the GitHub CLI has no cross-repository access from a session; a direct download is
refused by the sandbox), so no builder could push (pull request #678: the conductor pushed for it).
The owner ruled on 2026-11-06: keep the scan mandatory, and take the recommendation that works
for real projects, where builders also run in managed sessions.

## Decision

1. **A declared deferral.** When `gitleaks` is absent, `prepush.py`'s `secret-scan` step is `ok`,
   with one printed line, only when the body file (`--body`) carries the exact line
   `Secret-scan: deferred to CI` and the current branch is a builder branch (`claude/brief-<n>`).
   The line names the CI step that must pass before a merge. On any other branch the line is
   refused naming the rule; without the line the step is the FAIL of ADR-0306 decision 1,
   unchanged. `--quick` and `--record` keep their meanings.
2. **A present scanner always runs.** The line never replaces a scanner on `PATH`: with gitleaks
   present the scan runs and a finding fails the step, line or no line.
3. **The gate is CI, and it is unchanged.** `merge_cleared.py` merges only a head whose required
   `governance` check is green (SPEC-0039 rule 4), and that run's `Secret scan` step (ADR-0158,
   pinned by version and digest) fails the check on any finding over the branch's commits. So a
   deferred scan is still run, on the same commits, before anything reaches the default branch;
   what moves is where the first scan runs, never whether it runs.
4. **The rule.** Session rule 31 names the deferral in one clause and pays for it inside the same
   rule (`config/rule-budget.txt`: 3461 to 3453 words). Builders' standing instructions put the
   line in every body written from a cloud session.
5. **Amends ADR-0306 decision 1** by the exception of decision 1 above; every other decision of
   ADR-0306 stands (the pin, `--quick`, the other commands, the doctor line).

## Consequences

A cloud builder pushes again, and the honest record of where the scan ran is in the body line and
the prepush output. The scan on a developer's machine stays mandatory with no deferral outside a
builder branch.

## Residual

- 2026-11-06: a project whose CI has no `Secret scan` step would merge a deferred scan unscanned;
  the governance workflow the kit installs carries the step, and removing it changes a workflow,
  which is the owner's hold list. A doctor line naming a missing step is a later brief (due
  2027-01-31).

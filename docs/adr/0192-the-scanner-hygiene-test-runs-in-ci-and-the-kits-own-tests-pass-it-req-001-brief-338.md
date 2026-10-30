# ADR-0192: the scanner hygiene test runs in CI and the kit's own tests pass it (REQ-001, brief 338)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0010
- Requirements: REQ-001

Protected classes: `.github/`, `tests/kit/`

## Context

Brief #338 (priority 1): on 2026-10-30 `tests/kit/test_scanner_hygiene.py::test_bandit_finds_only_asserts_in_kit_source`
failed on the default branch wherever bandit is installed. Bandit reported two findings B105 (possible hardcoded password) on
test variables named after a password in `tests/kit/test_drift_unused_code.py` and `tests/kit/test_retired_requirements.py`.
CI did not see it: the test is skipped when bandit is not installed, and the step `Install tooling` of governance installed
only pytest and ruff. A check that is silently skipped in CI contradicts the kit's rule against silent skips (#289). The
builder reproduced the failure with bandit 1.9.4 installed (1 failed) before changing anything.

## Decision

1. **The two variables (answer 1).** The two test variables are renamed `canary`, which states their role: a text the
   test watches for in the output. No scanner ignore entry and no inline suppression is added.
2. **Governance installs bandit (answer 2).** The step `Install tooling` of `.github/workflows/governance.yml` installs bandit
   with pytest and ruff, on the same terms as them (Q-338-1). It then checks each of the three tools with
   `python -m <tool> --version` and fails the step naming the tool that is missing, so the hygiene test runs in CI and never
   skips there.
3. **Tests first (answer 3).** `tests/kit/test_scanner_hygiene.py` gains two tests: the install step names bandit beside pytest
   and ruff, and it fails by name on a tool it could not install. With bandit installed the hygiene test failed before the
   rename and passes after it.

## Consequences

A contributor with bandit installed sees the same green suite as CI, and a new bandit finding in kit source fails governance
instead of passing unseen. A project that installs the kit runs the same step, so its governance installs bandit as well.

## Residual

- 2026-10-30: pinning the tooling (pytest, ruff and bandit) is a later brief if the maintainers want it (Q-338-1).

## Log

- 2026-10-30, verdict on 9b0419f: Q-338-1 answered, bandit is installed unpinned, on the same terms as pytest and ruff; pinning
  the tooling is a later brief if wanted.
- 2026-10-30, verdict on 9b0419f: Q-338-2 answered, `.github/workflows/governance.yml` is changed in this pull request now that
  #329 has merged (merged into this branch from the default branch, no force-push).
- 2026-10-30, verdict on a5439ff: Q-338-3 answered, the full governance run of a5439ff failed only in `PR body shape`, having
  read the body from before its `Build-state row:` was dated; an edit cannot cure it because of the defect filed as #347
  (`full_run.py` counts the skipped `Post` steps of a failed job as not reached). This commit, which records Q-338-1 to Q-338-3
  here, starts a full run that reads the current body; #347 is not fixed in this pull request.

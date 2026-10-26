# ADR-0146: governance skips its heavy steps on a status-only final commit (REQ-039, brief #216 build c)

- Status: Accepted
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0137, ADR-0144
- Requirements: REQ-039

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #234 (build c of brief #216, priority 1): proof now skips the suite on a status-only final commit (ADR-0137), but governance still runs in full, about 5.5 minutes, and is the largest remaining cost of the last step of a pull request. The conductor assigned the brief to `builder-b` on #204 with this ADR number reserved. The tests were written first (`tests/kit/test_status_only_governance.py`: 19 failed and 3 passed on the unchanged tree).

## Decision

1. **One decision for proof and governance** (`scripts/agk/status_only.py`): the head is one commit after its parent, the commit changes only `- Status:` lines, the check passed on the parent, and the tip of the default branch is already in the parent. For governance the option `--parent-governance CONCLUSION` gives the conclusion of the full run of governance on the parent in place of proof's; only the reason changes (`governance in full did not pass on the parent`). The two options are not given together. No second copy of the decision is written; a test shows both options decide alike on the same commits.
2. **The step** (`.github/workflows/governance.yml`, `Status-only final commit`, on a pull request that is not an edited description): it reads the parent's workflow runs with one `GET` (`display_title == "governance full"`, the latest by `created_at`), passes its conclusion to the script, and on `skip` writes one line to the job summary naming the parent run it relies on. A moved base, a parent whose full governance run did not pass, a non-status change, a merge commit and an unreadable response all run in full. The job and its name stay, so the required check still reports; no write permission is added.
3. **Skipped on `skip`**, each by `if: ... && steps.status.outputs.skip != 'true'`:
   - `Install tooling`: installs pytest and ruff for the lint and the tests only, which are skipped.
   - `Lint`: runs ruff over the Python code and the tests, which a status line does not change.
   - `Tests of the checks`: runs the kit's unit tests of the scripts, which read the code, not the status lines.
   - `Project tests`: runs the project's own tests, which read the code.
   - `check_kit_tests`: checks that the kit's tests cover the checks, which reads the test files.
4. **Kept, because a status line can change their result** (or because it is cheap and I am unsure): every step that reads statuses, numbers, specs, ADRs, requirements, approvals or the body (`check_protected_changes`, `check_requirements`, `check_adrs`, `check_numbers`, `check_specs`, `check_build_state`, `check_design`, `check_pr_mode`, `check_final_clearance` above all, the body steps), `check_neutrality` and `Secret scan` (the text after `- Status:` is free, so a token or a secret could be in it; both are short), the reviewers checks and the release check (cheap). The setup steps and the `Latest full run` step are unchanged (Q-K4-322).
5. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-sk.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. Amendment 82 (`docs/runs/proposed-spec-amendments-82.md`) is for SPEC-0007 rule 13 and SPEC-0010 rule 17. It changes `.github/`, so the maintainer merges it.

## Consequences

- The last step of a pull request takes the time of the kept checks, not of the lint and the suites; a later description edit still finds a successful full run and passes as before.
- A status-only commit chain (two such commits in a row) can rely on a skipped run, whose code is the code of the last full run; the base condition holds at each step.

## Residual

- 2026-10-26: the status-only shape allows a `- Status:` line in any modified file, including a source file; a lint error in such a line is found by the next full run, not by the skipped one (due 2026-12-31).
- 2026-10-26: the parent's full run is found by the run name `governance full`; a rename of the run name makes every status-only commit run in full, never skip wrongly (due 2026-12-31).

# ADR-0116: checkpoints, draft pull requests and the progress line (REQ-040 part a, SPEC-0033 rules 1 to 3)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0113, ADR-0100, ADR-0109
- Requirements: REQ-040

Protected classes: `.github/`, `config/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0033 (Approved, #189) rules 1 to 3 are build (a) of brief #182. The tests were written first (`tests/kit/test_draft_and_progress.py`; on the unchanged tree: 17 failed).

## Decision

1. **Rules file** (rules 1 and 3): `config/session-rules.md` gains rule 7 (a checkpoint at every step that leaves the tests green or expected-red, subject `checkpoint:`, the first one opens a draft pull request, never a `Final:` line, ready for review only when the builder's own checks pass) and rule 8 (one `Progress: <head> done <n>/<m>; next: <step>` comment, edited in place and never repeated).
2. **Drafts** (rule 2): `check_pr_body.py --draft VALUE` and `check_final_clearance.py --draft VALUE` print `skipped (draft pull request)` and pass when the value is `true`, and check as before for any other value; the workflow `.github/workflows/governance.yml` passes `github.event.pull_request.draft` to both steps and runs on `ready_for_review`, so marking a pull request ready checks it. Neither script calls GitHub.
3. **The progress comment** (rule 3): `session.progress_of(comments, login)` returns the one `Progress:` comment of the pull request's author as `{head, done, total, next}` with the problems (more than one, or malformed), each naming the rule and never the line; it is a function for build (b), where `session.py resume` prints it. No command is added here (Q-K4-276).
4. Flow mode: no version bump, the fragment `changelog.d/ccr-7649d887-m9hvn7-ba2.md`, `CHANGELOG.md` and `kit/hashes.json` as on main. Amendment 56 (`docs/runs/proposed-spec-amendments-56.md`) is the one-sentence proposal to SPEC-0032 that SPEC-0033 rule 11 asks build (a) to carry.

## Consequences

- A builder's work is on its branch and visible as a draft from its first step; the body and clearance checks wait for the ready state.
- The router and `queue` of SPEC-0032 must honour the draft sentence when they are built.

## Residual

None beyond SPEC-0033's.

# ADR-0111: the base of a pull request run is the first parent of the merge ref (brief #180)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0108, ADR-0112
- Requirements: REQ-009

Protected classes: `.github/`, `tests/kit/`, `tests/kit_dev/`

## Context

#175 and #178 went red on `check_protected_changes` with no fault of their own. `governance.yml` and `proof.yml` set `AGK_BASE: ${{ github.event.pull_request.base.sha }}` for the whole job, while `actions/checkout` checks out the merge ref, a merge of the current base branch and the head. When another
pull request merged after the event's base sha was taken, the sha is older than the first parent of the merge commit, `merge-base BASE HEAD` returns that older commit, and every check that diffs against the base counts the other pull request's files (on those runs the diff from 52023b3 held #177's `docs/requirements.md`).

Measured here before the fix, with real merge commits (the first four tests of `tests/kit_dev/test_merge_ref_base.py` passed on unchanged code): with `AGK_BASE` the stale sha, `check_protected_changes` fails on a `docs/requirements.md` merged meanwhile, `check_build_state` fails on a `docs/build-state.md` merged meanwhile, `kit_hashes` counts the other pull request's fragment and
fails "exactly one fragment", and `check_release` reads a release merged meanwhile as this pull request's release (rule 5); with `AGK_BASE` the first parent of the merge commit every one of them passes. The other base-dependent code (`check_adrs`, `check_specs`, `proof.py`, `intake.py`) reads the same base and gets the same fix from the same step; no failing scenario was built or measured for them, so this decision does not claim they were failing.
pull request made to an Accepted ADR or an Approved spec, which no merged change can leave failing, so no failing scenario is built for them.

## Decision

1. **One step**, `Base of the merge ref`, in `.github/workflows/governance.yml` and in `.github/workflows/proof.yml` (the two workflows that set `AGK_BASE`), right after the checkout and before any step that reads the base, and **the only place that sets `AGK_BASE`**: the job-level
   `env: AGK_BASE` is removed. The first version of this decision kept the job-level value and let the step override it through `$GITHUB_ENV`; the review of 4f06311 pointed out that whether a `$GITHUB_ENV` value overrides a job-level `env:` value is the whole fix and was proved neither by the tests
   (they cannot run Actions) nor by this pull request's own run (its base was not stale), so the question is removed instead of answered. For a `pull_request` run the step reads the event's base sha from a step `env` (`EVENT_BASE`); when `HEAD` is a merge commit (`git rev-list --parents -n 1 HEAD`
   lists three words) it takes `git rev-parse HEAD^1`, else `EVENT_BASE`, and appends `AGK_BASE=<that>` to `$GITHUB_ENV` unless it is empty. A `push` run has no step and no `AGK_BASE`, as before (the job-level value was the empty event sha there).
2. **Tests** (`tests/kit_dev/test_merge_ref_base.py`, kit-only): the four checks above on a real merge commit, each passing with the first parent and failing with the stale sha; the step's own shell text, extracted from both workflows and run in a repository, writes the first parent for a merge commit even when the event's base is
   stale, the event's base for a checkout with one parent, and nothing when there is neither; neither workflow keeps an `AGK_BASE:` key, the step is the only writer, it comes after the checkout and before the first check, for pull requests only. `tests/kit/test_workflow.py` (a protected path, named above) had a test that required
   the job-level value; it now requires that no job-level value remains and that the step sets it from the event's base sha, for `governance.yml`.
3. **The guide**: `docs/guides/getting-started.md` troubleshooting names the symptom (a check fails on files the pull request did not change) and the fix.
4. **Flow mode** (SPEC-0031): installed files change (`governance.yml` and `proof.yml` are written by the installer), so the fragment is `changelog.d/188.md`; the table is not edited.

## Consequences

- A pull request is no longer failed for files another pull request merged between its base sha and the merge ref; the rule and the checks are unchanged.
- The workflows are installed verbatim, so a project gets the step on its next `agk upgrade`.

## Residual

- 2026-10-25: a pull request whose merge ref cannot be made (a conflict) has no CI run at all, as before; the conflict end of `session.py watch` covers it (due 2026-12-31).
- 2026-10-25: the checks still compare with the merge ref made when the run started; a main that moves during the run is not seen until the next run (due 2026-12-31).

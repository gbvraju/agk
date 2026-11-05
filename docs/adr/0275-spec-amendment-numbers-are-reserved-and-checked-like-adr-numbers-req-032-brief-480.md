# ADR-0275: spec-amendment numbers are reserved and checked like ADR numbers (REQ-032, brief 480)

- Status: Accepted
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0083, SPEC-0025
- Requirements: REQ-032

Protected classes: `.claude/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #480 (found-bug, plan #542 wave 1): three parallel pull requests (#463, #464, #466) each
added `docs/runs/proposed-spec-amendments-108.md` while 108 was reserved for a fourth brief, and
every pair conflicted add/add. ADR numbers are reserved per brief in the conductor's field note;
amendment numbers were not, and `check_numbers.py` (ADR-0083, SPEC-0025 rule 1) compared only
requirement, spec and ADR numbers inside one checked-out tree. Two pull requests that add the same
file never meet in one tree, so nothing caught it before the conflict. The conductor's field note
on #480 gives the answers this ADR records.

## Decision

1. **The check** (answer 1). `scripts/agk/check_numbers.py` also reads the amendment files
   (`docs/runs/proposed-spec-amendments-<n>.md`) that the pull request adds, against the merge base
   with the base ref that `common.resolve_base` finds (`AGK_BASE`, `GITHUB_BASE_REF`, then the
   default branch). It fails under rule 1 when the base ref already has that file
   (`amendment <n> is on the default branch`). With `--open FILE --number N`, a saved
   open-pull-requests file read as `check_pr_mode.py` reads one (`common.json_records`), it also
   fails when another open pull request's record lists that path in its `files` list
   (`amendment <n> is also added by #<m>`). A record without a `files` list of paths, and the
   record of the pull request's own number, are not compared: the check names a number and a pull
   request only from a listed path, never from a title. `--open` without `--number` and any other
   option are a usage error (exit 2), because without its own number a pull request would match its
   own record. When no base ref resolves outside CI, only the tree part runs, as before. It reads
   files and git only; no network.
2. **The reservation** (answer 2). `.claude/agents/conductor.md` and `docs/briefs/TEMPLATE.md` say
   that a brief which adds a spec amendment has its amendment number reserved in the brief's field
   note, as its ADR number is.
3. **Tests first** (answer 3): `tests/kit/test_check_numbers_amendments.py` with fixture
   repositories and a saved open-pull-requests file. No new script, so `kit/manifest.json` is
   unchanged; one changelog fragment, no version bump.

## Consequences

- A pull request that takes an amendment number the default branch already has fails governance
  with the number named, before a person meets the add/add conflict; `intake.py renumber` does not
  move amendments, so the builder renames the file by hand to the reserved number.
- The open-pull-requests part runs only where a file with each open pull request's added paths is
  given; the governance workflow does not write one yet (`Q-480-1`).

## Residual

- 2026-11-04: the governance workflow's open-pull-requests file holds only numbers; writing each
  open pull request's file list into it (or a second file) is left to a later brief (`Q-480-1`).

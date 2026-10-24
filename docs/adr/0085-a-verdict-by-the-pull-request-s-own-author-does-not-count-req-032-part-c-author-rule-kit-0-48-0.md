# ADR-0085: a verdict by the pull request's own author does not count (REQ-032 part c, the author rule, SPEC-0025 rule 4), kit 0.48.0

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0082, ADR-0083, ADR-0084
- Requirements: REQ-032

Protected classes: `.claude-plugin/`, `.github/`, `agk.toml`, `kit/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0025 (Approved) part (c) is the author rule, `Depends-on` and `pr_mode` (rules 4 to 7). Its estimate is about 280 lines of code and 400 of tests, over the 600-line limit of one pull request, so it is split in
two as the spec expects: this pull request is the author rule (rule 4, AC4); the next is `Depends-on` and `pr_mode` with their workflow fetches (rules 5 to 7, AC5 to AC8). With two or more listed verdict authors a
verdict by the pull request's own author must clear nothing; with one nothing changes.

## Decision

1. `metrics.counted_authors(authors, own)` returns the listed authors whose verdicts count on a pull request by `own`: with two or more distinct listed logins the own login is dropped (compared without case,
   a leading `@` ignored); with one, an empty login or an empty list nothing changes.
2. The metrics (`build_record`) and the facts (`pull_record`) read the login from the pull request record (`user.login`) and pass the counted authors to the existing verdict readers, so the dropped verdicts are no
   review round, no clearance, no rejection and no `Final:` cover.
3. `check_final_clearance.py` takes `--author LOGIN` and applies the same rule to the latest covered fix list; without it nothing changes. `.github/workflows/governance.yml` passes the pull request author's login
   from the event (`github.event.pull_request.user.login`). Its permissions and fetches are unchanged.
4. Amendment 44 (`docs/runs/proposed-spec-amendments-44.md`) is applied to SPEC-0021 rule 5 and SPEC-0007 rule 5.
5. Tests first (`tests/kit/test_self_clearance.py`): `counted_authors` cases, the metrics with two and one listed authors, the facts, the check with and without `--author`, and the workflow line.
6. **Kit 0.48.0**: the manifest `kit_version`, the hashes, the plugin version and `version` in this repository's `agk.toml`.

## Consequences

- In a repository with two or more listed verdict authors, an author can no longer clear their own pull request; with one listed author the person who wrote the pull request may still clear it.
- This repository lists one verdict author today, so nothing changes here.

## Residual

None.

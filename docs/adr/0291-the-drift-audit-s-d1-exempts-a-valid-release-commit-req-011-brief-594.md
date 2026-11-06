# ADR-0291: The drift audit's D1 exempts a valid release commit (REQ-011, brief 594)

- Status: Proposed
- Date: 2026-11-05
- Deciders: maintainers
- Related: ADR-0012, ADR-0277, SPEC-0004, SPEC-0028
- Requirements: REQ-011

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0004 rule 6 applies the rule of `check_protected_changes` per first-parent commit, but without
its release exemption (`release_pull_request`, SPEC-0028). Drift audit #150 had 31 findings, and 30
were D1 on release commits for `.claude-plugin/`, `agk.toml` and `kit/`, each one a release the
per-pull-request check had passed. False findings bury real drift. The ADR number and amendment
121 were reserved by brief #594.

## Decision

1. D1 asks the kit-only `check_release.valid_release` about a first-parent commit that raises
   `version` in `agk.toml`. The commit's release part (its changes to the five release files of
   SPEC-0028 rule 4, its deleted fragments under `changelog.d/` and its edits of `docs/adr/`) is
   laid on its parent in one temporary shared clone outside the checkout, removed after the run;
   the repository and its `.git` are not written.
2. A valid release part yields no D1 finding for its files. Any other protected file of the commit
   is judged as before, so its class is still a finding unless an ADR of the commit names it.
3. The release check reads the Final comments of the parent's records from a new option
   `--comments FILE` of `drift_audit.py` (SPEC-0021 rule 3a, as #558 made the release check read
   them). Without them while the parent holds a record, or with an unreadable file, nothing is
   exempt. An installed copy, which has no `check_release.py`, exempts nothing.
4. SPEC-0004 rule 6 changes by amendment 121 (`docs/runs/proposed-spec-amendments-121.md`),
   applied in the same pull request; it needs a person's `Approve: SPEC-0004`.

## Consequences

The audit of 2026-10-31 on the default branch reports `D1=0` instead of `D1=30`. The weekly
workflow does not pass `--comments` yet, so a release whose parent holds a record is still a
finding there until the workflow saves the record comments (a workflow change needs its own ADR).

## Residual

- 2026-11-05: `.github/workflows/drift-audit.yml` does not save the record comments for `--comments` (Q-594-1) (due 2026-12-31).

# Proposed spec amendments 121 (SPEC-0004; REQ-011)

Date: 2026-11-05 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0291 (brief #594), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0004-drift-audit.md`.
The number 121 is the one brief #594 reserved. This amendment is applied to the spec text in the same pull request. It
needs a person's `Approve: SPEC-0004` on the pull request; no session posts it.

1. **D1 exempts a valid release (rule 6).** Rule 6 gains, after its last sentence: a valid release is exempt, as the
   per-pull-request check exempts a valid release pull request (SPEC-0028 rules 4 and 5). When a commit raises
   `version` in `agk.toml`, its release part (its changes to the five release files, its deleted fragments under
   `changelog.d/` and its edits of `docs/adr/`) is laid on its parent in a temporary copy outside the checkout,
   removed after the run, and `check_release.valid_release` judges it with the Final comments of the parent's records
   given by `--comments FILE` (SPEC-0021 rule 3a; without them while the parent holds a record, no exemption). A valid
   release part yields no finding for its files; any other protected file of the commit is judged as before. The
   release check is kit-only, so an installed copy of the audit exempts nothing. Nothing else of rule 6 changes.

Why: drift audit #150 (run of 2026-10-31) had 31 findings, 30 of them D1 on ten release commits for `.claude-plugin/`,
`agk.toml` and `kit/`; the per-pull-request check had passed each one as a valid release. Measured on the default
branch with `--today 2026-10-31`: `D1=30` before, `D1=0` after.

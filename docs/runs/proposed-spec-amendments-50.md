# Proposed spec amendments 50 (SPEC-0008, SPEC-0025; REQ-035)

Date: 2026-10-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0096. The paths: `docs/specs/0008-upgrade.md`, `docs/specs/0025-a-team-can-run-independent-pull-requests-in-parallel-without.md`.

1. **SPEC-0008, the bump rule (rules 22 and 25).** In flow mode (`pr_mode = "flow"`) the rule that a change to an installed path needs a `kit_version` bump is replaced, for a pull request that leaves the version as it is, by this: the pull
   request adds at least one new line under `## Unreleased` of `CHANGELOG.md` (SPEC-0028 rule 2). The row of the current version in `kit/hashes.json` then lists the digest of each build beside the earlier ones, which the table
   already allows, and the rows of earlier versions are never touched. In strict mode the rule is unchanged.
2. **SPEC-0025 rule 8, the release model.** Kit build pull requests do not bump the version in flow mode; one release pull request bumps `agk.toml`, `kit/manifest.json` and the plugin together, moves the Unreleased lines of
   `CHANGELOG.md` under the new version and adds the new row of `kit/hashes.json`; `scripts/agk/check_release.py` checks it (SPEC-0028 rules 4 and 5).
3. **SPEC-0025 rule 6, the session's rule.** `CLAUDE.md` rule 2 and principle 3 say: never stacked on another's unmerged change, a dependence is declared with `Depends-on: #n`, one open pull request per session, several sessions may
   have one each in flow mode, and in strict mode a person has one open pull request at a time.

# ADR-0379: The test map's ignore line and the one test of the released `.gitignore` (REQ-062, brief 812)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0360, SPEC-0055, brief #812, Q-812-1
- Requirements: REQ-062

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`, `tests/kit_dev/`

## Context

SPEC-0055 build (c) writes a generated map to `.agk-test-map.toml`, which is never committed
(principle 5), so brief #812 answer 3 adds that name to `kit/templates/gitignore`. ADR-0360 decision
5 lets the builds of SPEC-0055 change `kit/` and says no build changes `tests/kit_dev/`. The line
cannot land inside that decision: `test_a_real_install_of_the_last_release_with_a_project_line_upgrades`
in `tests/kit_dev/test_upgrade_project_lines.py` reads the current template and asserts that its hash
is the text of release 0.57.1, so while it stands the template can never change. Session rule 36 has a
build write its own ADR when it changes a decision of the ADR that covers it, and principle 11 has a
check changed only by an ADR. The ruling on Q-812-1 and the `Correction:` on the pull request give
this build this ADR, the number reserved on the brief's `taken:` line.

## Decision

1. This ADR changes decision 5 of ADR-0360 for one test only: this build may change
   `test_a_real_install_of_the_last_release_with_a_project_line_upgrades`. No other file or test under
   `tests/kit_dev/` changes, and decision 5 stands for every other build of SPEC-0055.
2. The test writes out the released 0.57.1 text instead of reading the current template. It still
   proves that text's hash is in the release's row of `kit/hashes.json`, and it still proves the
   upgrade yields the current template's block followed by the project's line.
3. `.agk-test-map.toml` is added to `kit/templates/gitignore` and to the repository's own `.gitignore`
   block, which `test_the_kit_names_gitignore_as_its_only_extendable_file` requires to equal the
   template's.
4. This ADR replaces `Covered-by: ADR-0360` for this pull request and names every protected path
   class it changes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml` and `tests/kit_dev/`. ADR-0360
   holds for everything else in this build, and `kit/hashes.json` and the version stay the release's.

## Consequences

A project that installs or upgrades the kit ignores the generated map from then on. The test no
longer ties the template to one release, so a later build can add an ignore line without touching it.

## Residual

None.

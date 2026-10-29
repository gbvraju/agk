# ADR-0169: the real-table upgrade test names release 0.57.1 (REQ-039, brief 295)

- Status: Accepted
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0164, ADR-0108
- Requirements: REQ-039

Protected classes: `tests/kit_dev/`

## Context

Brief #295 (priority 1), found on the release pull request #292 (brief #291, Q-291-1). The test
`tests/kit_dev/test_upgrade_project_lines.py::test_a_real_install_of_the_last_release_with_a_project_line_upgrades`
(brief #269, ADR-0164) took "the last release" as the highest row of `kit/hashes.json` and asserted that its
`.gitignore` is the text of `kit/templates/gitignore`. That holds only while 0.57.1 is the newest row. The release of
0.57.2 adds a row whose `.gitignore` is the marked block, so the test failed on #292 at 8f574ed (1 failed) and passed
on origin/main 3307c57 (1 passed), although nothing was wrong. A release pull request may change only its five release
files (SPEC-0028, ADR-0108), so the test would block every later release.

## Decision

1. **The release the test means** (answer 1). The test names 0.57.1, the last release whose `.gitignore` is the bare
   template, as `BARE_GITIGNORE_RELEASE`, and asserts that the row is in the table; it no longer takes the newest row.
   The install, the project line, the upgrade and what it asserts are unchanged.
2. **Proof** (answer 2). The test file passes on origin/main and with the table of #292, whose newest row (0.57.2)
   has the marked block: 12 passed on both.
3. No kit script changes and no changelog fragment: `tests/kit_dev/` is not installed in a project. This ADR exists only
   because `tests/kit_dev/` is a protected path class (answer 3).

## Consequences

- A new release no longer breaks the test; the release 0.57.2 (#292) depends on this change.
- The test keeps proving the migration from the last bare-file release to the marked block.

## Residual

None.

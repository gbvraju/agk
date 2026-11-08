# ADR-0334: the prototype checks of check_design.py and their test map entry (REQ-044, brief 458)

- Status: Proposed
- Date: 2026-11-07
- Deciders: maintainers
- Related: ADR-0204, ADR-0248, ADR-0249, ADR-0252, ADR-0285, SPEC-0037
- Requirements: REQ-044

Protected classes: `scripts/agk/`, `kit/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0037 (Approved; ADR-0204) has `check_design.py` check each prototype version folder before any demo (rule 7), allow
only the kit's hashed runtime and the folder's two stylesheets in it (rule 5), and read the reflow record of rule 8.
Brief #458 is build (d) of rule 14, after the writer of #457 (ADR-0252). The build itself changes no decision of the
spec, so the conductor asked for `Covered-by: ADR-0204`. But ADR-0204 decision 3 says no build changes `agk.toml` of
this repository, and the kit's own test `tests/kit_dev/test_intelligent_testing.py` fails unless every script under
`scripts/agk/` has a `[[testing.map]]` entry in `agk.toml` (ADR-0285), whose comment says a change of the map needs an
ADR. So this one change of a decision, for one table of `agk.toml`, is recorded here, with the classes the build changes.

## Decision

1. **The module (answer 1).** `scripts/agk/design_prototype_check.py` is new and installed (`verbatim` in
   `kit/manifest.json`, sorted). It holds `RUNTIME_HASHES` (the SHA-256 of each released `agk-prototype.js`, oldest
   first; today one, `// agk-prototype 1`), and `FIXTURE_EMAILS`, `FIXTURE_HOSTS` and `FIXTURE_PHONES` (the values of the
   kit's `fixtures.json`), so the installed check never reads the kit (`Q-S0037-5`, `Q-457-3`). `check_design.py`
   `cmd_check` calls `version_problems(root, version)` for each `docs/design/prototype/v<n>/` that holds a file.
2. **The failures (answer 2).** Each is `rule 5|7: docs/design/prototype/<version>/<screen>--<state>: <what>` (a folder
   file stands where the screen is for a folder-wide problem) and never names the value found: the inventory's pages
   (an `n/a:` state needs no page), links and loaded files outside the folder, scripts other than the runtime at the end
   of the page or a runtime whose hash is not listed, `link` elements other than `standard.css` and `theme.css`,
   `@import`, `url()` outside the folder, colours outside the tokens (`colour_problems`), the contrast pairs of
   `design_standard.CONTRAST_PAIRS` in light and dark from the two stylesheets, placeholders, data outside the fixture
   constants, and the accessibility and layout basics of rule 7.
3. **Reflow (answer 3).** A `sideways` entry of `screenshots/reflow.json` fails
   `rule 8: <version>/<screen>--<state>: the page scrolls sideways at <breakpoint> px`; an absent record, a `not run`
   entry or a missing entry prints `design: reflow not run (<version>)`, information and never `ok` for reflow; a
   record that cannot be read fails naming rule 8 and the file.
4. **Mockups (answer 4).** The folders of `docs/design/mockups/` keep `mockup_problems` unchanged.
5. **The test map.** `agk.toml` gains one `[[testing.map]]` entry for `scripts/agk/design_prototype_check.py`, and the
   new test file `tests/kit/test_check_design_prototype.py` is added to the entries of the scripts it imports or runs
   (`check_design.py`, `design.py`, `design_inventory.py`, `design_prototype.py`, `design_signoff.py`,
   `design_standard.py`). Nothing else of `agk.toml` changes. This amends ADR-0204 decision 3 for this table only.

## Consequences

A prototype version with a missing state, a broken link, a stray script or stylesheet, a colour or contrast off the
standard, a placeholder, data outside the fixture set or an accessibility or layout gap fails `check_design.py` before
a demo, naming the rule and the screen. A project's existing mockup folders and themes read as before. A new runtime
release must add its hash to `RUNTIME_HASHES` in the same pull request; the kit test that the kit's runtime has the
newest hash catches a forgotten one. The changelog fragment is `changelog.d/design-prototype-check.md`.

## Residual

- The format of `reflow.json` is this build's reading (`Q-458-2`), which #461 must write; until it does, every version
  reads `reflow not run`.
- Data outside the fixture set is caught only for email addresses, link hosts and phone numbers in three common forms;
  names and other phone forms stay with the person's review (SPEC-0037 residual of 2026-10-30).
- The checks are static: a width set by a script or by a value the check does not parse is left to the reflow test of
  rule 8.

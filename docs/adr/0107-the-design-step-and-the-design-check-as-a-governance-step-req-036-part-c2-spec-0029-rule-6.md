# ADR-0107: the design step, and the design check as a governance step (REQ-036 part c2, SPEC-0029 rules 6, 7 and 9)

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0097, ADR-0099, ADR-0104
- Requirements: REQ-036

Protected classes: `.github/`, `agk.mk`, `kit/`, `scripts/agk/`, `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0029 (Approved, #166) splits its build into (a) engines and doctor, (b) vision and stack (both merged) and (c) design. Part (c) was split at its measure (ADR-0104, the maintainers read the split as intended on #174): (c1)
the check is merged, and this is (c2): `/agk:design` with its templates, and the governance step for `check_design.py` that the verdict on #174 put in this part (Q-K4-261, ruled), with the removal of the exemption in
`tests/kit/test_agk_mk.py`. The tests were written first (`tests/kit_dev/test_design_write.py`; on unchanged `main`: 27 failed, none passed). This pull request branches from the default branch. The number 0107 is the one the
verdict on #174 gave (0105 is held by #175 and 0106 is reserved on #171).

## Decision

1. **The writer** (kit-only, `scripts/agk/design.py`): `write --name NAME [--date D] [--theme-file F]` makes `docs/design/theme.md` only when it is absent (from the engine's draft, which is copied as given and then checked by
   `check_design.py`, or from `kit/templates/design-theme.md`) and the mockup folder `docs/design/mockups/<date>-<name>/` with `index.html` and `README.md` from `kit/templates/design-index.html` and `design-readme.md`. The date
   is the clock's (`date -u` semantics, UTC) unless given as a real `YYYY-MM-DD`; the name is a lower-case slug of at most 50 characters; an existing folder is never overwritten and an existing theme is never touched. The README
   holds `Approved: not yet`: the approval line `Approved by <name> on <date>` is the owner's and no script or template writes it. No network, no model.
2. **The screenshots**: `screenshots --folder FOLDER` takes four pictures (`screenshots/360-light.png`, `360-dark.png`, `1280-light.png`, `1280-dark.png`) with the first headless browser found on PATH (`chromium`, `chromium-browser`,
   `google-chrome`, `google-chrome-stable`, `chrome`), run with a fixed argument list and no shell; the dark ones add `--blink-settings=preferredColorScheme=1` (verify against the installed browser). With no browser it prints
   `design: no headless browser found; screenshots skipped` and succeeds; a folder that is not a mockup folder is refused.
3. **The templates** (`kit/templates/design-theme.md`, `design-index.html`, `design-readme.md`): the theme holds the Brand section with a source line per value and bracketed placeholders, one token block (light and dark, hex), the
   Contrast pairs, the rules of SPEC-0029 rule 6 (one token block, contrast of 4.5:1, status as word plus colour, native controls, 44 px targets, 360 px to wide, a system font, no script, no external request) and the Evidence
   line; the page uses the same tokens and passes `check_design.py` with placeholders in brackets. What `write` makes reads "not approved yet" and "placeholder brand" and does not fail.
4. **The skill**: `skills/design/SKILL.md` (user-only; it writes files and never commits) says that the engine named by `design` in `[engines]`, or the template, only drafts; that an engine never decides, never approves and never
   edits a protected file; that the owner gives each brand value and its source; and that the session never writes the approval line. `docs/guides/reference.md` lists the command and no longer calls the check kit-only.
5. **The governance step** (Q-K4-261, ruled): `check_design.py` is installed: `kit/manifest.json` lists it among the verbatim files, `agk.mk` runs it in `agk-governance` (after `check_kit_tests.py`, so `check_final_clearance.py` stays the
   last step) and `.github/workflows/governance.yml` has a step `check_design`. A project with no `docs/design/` sees `ok design (no design record)`. The exemption of `check_design.py` in `tests/kit/test_agk_mk.py` is removed,
   and `check_design.py` leaves the kit-only set of `tests/kit_dev/test_kit_manifest.py` (`design.py` joins it). An installed check needs its tests in the kit_tests folder (`check_kit_tests.py`), so `tests/kit_dev/test_check_design.py` moves to `tests/kit/test_check_design.py`, unchanged but for its imports. The counts of governance steps in `tests/kit/test_workflow.py` and `tests/kit_dev/test_init.py` rise by one (twelve checks to thirteen), as the counts of doctor checks did in ADR-0099. The weekly report's At risk section still does not read `at risk design: placeholder brand` (see the residual).
6. **No default engine, no version bump** (flow mode, SPEC-0028): one line under Unreleased in `CHANGELOG.md`; `kit/hashes.json` is refreshed by the script. The templates, the writer and the skill are plugin files.

## Consequences

- An owner can go from a brief idea to a vision, a stack and a first mockup, each approved by the owner's merge or line before the next; the design step ends with a mockup the check has passed and the owner has not yet approved.
- Every installed project runs the design check in `make governance` and in CI; it passes silently where there is no design record, so no existing project changes behaviour.
- The installed `agk.mk`, `governance.yml` and `check_design.py` change, so a project gets them on its next `agk upgrade`.

## Residual

- 2026-10-24: wiring `at risk design: placeholder brand` into the weekly report's At risk section changes SPEC-0016 and the facts schema, which the maintainers decide (due 2026-12-31).
- 2026-10-24: the screenshots depend on a headless browser and on flags that are not confirmed for every browser (verify); a project without one gets the note and no pictures (due 2026-12-31).

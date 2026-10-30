# ADR-0201: the reference guide lists the minutes, test plan and core audit commands (REQ-020, brief 341)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0184, ADR-0185, ADR-0188
- Requirements: REQ-020

Protected classes: `tests/kit_dev/`

## Context

Brief #341 (priority 2): #324, #325 and #328 each deferred their line in `docs/guides/reference.md`, because another open
pull request was changing that file (Q-324-1, Q-325-2, Q-328-1). A person looking up the kit's commands did not find the
Actions minutes report, the test plan or the core audit. The brief also asks for a test so that a future command cannot be
missed. That test lives in `tests/kit_dev/`, a protected path class, so this ADR names it (Q-341-3). The tests were written
first (`tests/kit_dev/test_reference_commands.py`: 10 failed, 2 passed at the first checkpoint of the pull request).

## Decision

1. **One section each (answer 1, Q-341-1).** `docs/guides/reference.md` gains `## Actions minutes`, `## Test plan` and
   `## Core audit` after `## Local mode`, in the page's existing section format: an indented command line with the options of
   the script's usage, one plain sentence of what it does, a short paragraph, and a link to where it is explained
   (`project-ci.md#how-many-minutes-are-left`, `existing-codebase.md#step-4-tell-the-proof-check-how-to-run-your-tests`, and
   ADR-0188 for the core audit, which has no guide). The page's only table lists the plugin's slash commands, and these three
   scripts have none.
2. **Nothing else changes (answer 2).** No other section is written.
3. **No command is missed (answer 3, Q-341-2).** `tests/kit_dev/test_reference_commands.py` fails when an installed kit script
   (`scripts/agk/*.py` of `kit/manifest.json`) is named nowhere in the reference, unless the kit itself runs it (it is named in
   `agk.mk` or an installed workflow) or another installed script imports it. One named exception list holds `check_brief.py`,
   a person's own check of a saved brief (SPEC-0030 rule 4), with one line saying why; a second test fails when an exception
   is named in the reference or no longer installed, so the list can only shrink.
4. **The fragment.** `changelog.d/reference-commands.md` also carries solo mode's marker, `(opt-in: review_mode)`, which a
   build could not add to the solo fragment (ADR-0193 residual; the field note of the conductor on the brief), so an upgrade
   to 0.60.0 lists `review_mode`.

## Log

- 2026-10-30, verdict on 4450dbe: Q-341-1 yes, one `## ` section each after `## Local mode`, the core audit linking to
  ADR-0188; Q-341-2 the reading is accepted, `check_brief.py` in the named exception list with one line saying why, and no
  other section written; Q-341-3 (a), ADR-0201 reserved, since every kit test folder is protected.

## Consequences

- The three commands of 30 Oct 2026 are in the reference, each with its options and a link.
- A new installed script that a person runs, and that the kit neither runs nor imports, fails the kit's tests until the
  reference names it or a brief adds it to the exception list.

## Residual

- `check_brief.py` has no section in the reference; a later brief may write one and remove it from the exception list
  (2026-10-30).

# ADR-0112: the red default branch, a literal date meeting a test that rewrites the day (brief #185)

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0105, ADR-0107
- Requirements: REQ-009

Protected classes: `.claude/`, `scripts/agk/`, `tests/kit_dev/`

## Context

Governance is red on main at 08ae27c (the merge of #178), step "Tests of the checks". Brief #185 first named the current row of `kit/hashes.json` as the cause; the conductor corrected it after a measurement that this pull request had made independently: the one failing test is
`tests/kit_dev/test_init.py::test_ac1_second_run_reads_the_stamped_date` (`1 failed, 2658 passed, 3 skipped` with the full suite), its second install reports one conflict, `.claude/agents/conductor.md`, and that file quotes a date in its own text ("read by the maintainers on 2026-10-25"). The test simulated an install
made on another day by replacing today's date in every installed `.md` and `.toml` file, which rewrote the quoted date of a kit document on the day it named (four files on 2026-10-25: three stamped by the installer, `conductor.md` not). Counterfactual, in a scratch directory: first install exit 0; the rewrite, then a second install, exit 1 with that one conflict;
the date restored in `conductor.md` alone, second install exit 0, table untouched. `init.py`, `adopt.py` and `upgrade.py` need no change.

## Decision

1. **The conductor role** (answer 1, `.claude/agents/conductor.md`): the literal date is removed, the documentation address stays. #184 removes the same date in its own pull request; whichever merges second keeps the file as the first left it.
2. **The test** (answer 2, `tests/kit_dev/test_init.py`): `test_ac1_second_run_reads_the_stamped_date` simulates an install made on another day by rendering the stamped templates again with that day, through `init.build_items` in a fresh directory of the same name, and writes only the files that differ (`agk.toml`, `constitution/vision.md`,
   `docs/adr/0001-adopt-agk.md`). No other file is touched, whatever it says. A test copies the kit, makes a kit document quote today's date, installs, restamps and installs again: nothing to do; a control test shows that rewriting every occurrence of the date reports a conflict on that document.
3. **The check** (answer 3, `tests/kit_dev/test_no_literal_dates.py`, a kit test and not a change of `check_neutrality.py`, which every project runs): no installed file, the verbatim files and the sources of the templates, holds a literal `YYYY-MM-DD` date (`{{date}}`, `YYYY-MM-DD` and weeks such as `2026-W41` are not dates); a test of the scan itself.
4. **Three more installed files held a literal date** and would have failed the check: the contract notes of `.claude/hooks/architect_guard.py` and `.claude/hooks/conductor_guard.py` ("read from the Claude Code documentation on 2026-10-19") and an example in a refusal message of `scripts/agk/product_report.py` (`--today must look like 2026-10-14`). The dates are removed (the notes keep their `(verify)`, the
   message says `YYYY-MM-DD`) instead of being exempted, because an exemption would weaken the check. These dates could only have broken the suite on the days they name; the choice is put to the maintainers as Q-K4-268.
5. **No change to the table or to the installer.** Builds still never edit `kit/hashes.json`. The change touches installed files, so flow mode (SPEC-0031) requires one fragment, `changelog.d/186.md`.

## Consequences

- The default branch is green again once this merges, on this day and on any other.
- A kit document cannot quote a date again without a test failing at once, and the second-install test no longer reads the day it runs.

## Residual

- 2026-10-25: a date written in another form (`25 October 2026`) is not found by the scan; the kit's documents date their provenance by pull request, not by day (due 2026-12-31).

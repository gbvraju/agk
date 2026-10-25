# ADR-0112: the red default branch was a date-sensitive test, not the table (brief #185)

- Status: Proposed
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0108, ADR-0107
- Requirements: REQ-038

Protected classes: `tests/kit_dev/`

## Context

Brief #185 (priority 0) says governance is red on main at 08ae27c (the merge of #178), step "Tests of the checks", because a second run of the installer reports a conflict on files it installed itself: since #181 (ADR-0108) builds no longer refresh
the row of the current version of `kit/hashes.json`, so the row lacks the current digests of `scripts/agk/check_design.py`, `agk.mk` and `.github/workflows/governance.yml`, and "the installer reads that row". It asks that the installer and the upgrade treat a file equal to the
kit's own file as unchanged, whatever the table holds, and that ADR-0108's residual line be closed.

Measured on main at 08ae27c, 2026-10-25, with the full suite: `1 failed, 2658 passed, 3 skipped`; the one failure is `tests/kit_dev/test_init.py::test_ac1_second_run_reads_the_stamped_date`. The installer's report names one conflict, `.claude/agents/conductor.md`. That file quotes
a date in its own text ("read by the maintainers on 2026-10-25"), and the test rewrote every occurrence of today's date in the installed `.md` and `.toml` files to `2020-01-02` to simulate an install made on another day: on 2026-10-25 it rewrote four files, and three of them (`agk.toml`,
`constitution/vision.md`, `docs/adr/0001-adopt-agk.md`) are stamped by the installer, the fourth is not. Counterfactual, in a scratch directory: a first install exits 0; the test's rewrite followed by a second install exits 1 with that one conflict; restoring the date in `conductor.md` alone
makes the second install exit 0, with the table untouched. `init.py` and `adopt.py` do not read the table at all (`init.py` `classify` compares bytes with the kit's own file), and `upgrade.py` `whole_file` tests `data == new` before it asks the table. The test would also have failed on any day a vendored file quotes that day's date.

## Decision

1. **The test** (`tests/kit_dev/test_init.py`): `test_ac1_second_run_reads_the_stamped_date` rewrites the date only in the files the installer stamps with it, the destinations of the rendered templates (`manifest["templates"]`), through a helper `restamp`; a unit test shows that the helper rewrites a stamped file and leaves a vendored
   file that quotes today's date alone, and a test shows which installed files hold the date. The test no longer depends on the day it runs.
2. **The behaviour the brief asks for already holds, and is now tested** (`tests/kit_dev/test_upgrade.py`, the four cases of the brief on the fixture kit): after a build changes an installed file and leaves the table, a target holding the kit's own file is "nothing to do" on a first and a second run; a project edit of the same file is a
   conflict and nothing is written; a target holding the released copy, whose digest the row lists, is replaced as before; and `init.py` and `adopt.py` do not read the table. No change to `init.py`, `adopt.py` or `upgrade.py` is needed, and none is made.
3. **Builds still never edit the table** (ADR-0108): nothing is written to `kit/hashes.json`.
4. **ADR-0108's residual is not closed by this decision.** The brief expected that treating a file equal to the kit's own as unchanged would close it; it does not, because that was already true. What stays open is a project installed from an unreleased checkout of day A and upgraded from a
   later checkout: its file equals neither the later kit's file nor a digest of the row, so the upgrade reports a conflict for a file the project did not edit. The question is on the pull request (Q-K4-267).

## Consequences

- The default branch is green again once this merges, and stays green on any day.
- The upgrade's behaviour for an unreleased checkout is pinned by four tests, so a change that stops reading the kit's own file first fails them.

## Residual

- 2026-10-25: ADR-0108's residual (a consumer that reads the table of an unreleased checkout sees files changed since the last release as modified) stays open for the project-upgrade case above until the maintainers answer Q-K4-267 (due 2026-12-31).

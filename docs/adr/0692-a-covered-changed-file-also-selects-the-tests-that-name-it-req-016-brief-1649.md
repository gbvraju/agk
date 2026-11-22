# ADR-0692: A covered changed file also selects the tests that name it

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1649, SPEC-0055 rule 6 (widened here), ADR-0359, ADR-0220, bug #1636, brief #1638
- Requirements: REQ-016

## Context

Governance on d91eb148 (#1630) failed on `tests/kit/test_playbook_default.py`, a test the pull request's own proof never
ran. `python3 scripts/agk/test_plan.py --base 24c34dcf --head d91eb148` did not select it, though the change edits
`config/playbooks/default.toml` and the test names that path: `scripts/agk/impact.py` reads the name index only for a
changed file that no `[[testing.map]]` entry covers (SPEC-0055 rule 6), and the entry `config/playbooks/*.toml` lists 19
tests without it. Any curated entry can miss a test in the same way. The tests were written first
(`tests/kit/test_impact_data_files.py`: 2 failed, 30 passed on the unchanged tree).

## Decision

1. **The selection** (`scripts/agk/impact.py`, `select`). With `profile = "balanced"`, a changed file that an entry
   covers and whose entries select an existing test, that is not documentation, not a test file and matches no
   `always_full` glob, also selects every test file that names its path or its folder (`tests_naming`, the rule 6
   index). The reason printed is `(names <path>)`. A test already selected keeps the reason it was selected with, and a
   test file the change itself adds or edits is not added (it runs as the pull request's own test; adding it made the
   third proof run repeat it, `tests/kit/test_proof_regression.py`). The
   file is not unmapped and is not counted in `unmapped: <path> -> <k> tests that name it`. This widens SPEC-0055
   rule 6, which named only a file no entry covers; for that file nothing changes.
2. **What does not change.** A covered file whose entries select no existing test stays unmapped and full (brief #373,
   `test_a_stale_entry_stays_unmapped_and_full`). `thorough` stays full; `fast` reads only the map; `always_full` is as
   before. The curated entries, `map_source` (`curated` or `generated`, whose entries are read the same way),
   `pr_tests = "all"`, `execution = "local"` (prepush uses `impact.py`), personal mode (the sidecar run uses the same
   selection) and a project using the kit (its own tests are indexed the same way) read the same rule. A larger
   selection may reach `full_when_share`, which runs the full suite as designed. The entry `config/playbooks/*.toml`
   in `agk.toml` is not changed (the brief's Q-1).

## Consequences

A test that names a changed file runs in that pull request's proof even when the map entry forgot it, so it can no
longer first fail on the default branch after merge. Selections grow: the case above went from 262 to 390 regression
files. The `selected: <path> -> <k> tests` line still counts the entry and importer tests only.

## Residual

- 2026-11-21: SPEC-0055 rule 6's text still says "a file that no entry covers"; an amendment that names this ADR is
  for the spec's reviewer group (principle 6).

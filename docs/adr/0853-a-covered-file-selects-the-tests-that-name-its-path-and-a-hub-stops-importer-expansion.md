# ADR-0853: A covered file selects the tests that name its path, and a hub stops importer expansion

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2055, 2026-11-27T19:12:21Z)
- Related: ADR-0692 (decision 1 narrowed here), ADR-0393, ADR-0422, ADR-0348, ADR-0359, ADR-0650, ADR-0220, SPEC-0055 rules 2, 6 and 10, SPEC-0044 rule 1, brief #2055, brief #1649, brief #878, plan #661
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

No kit pull request ran a selection: of 43 pull request governance runs from 2026-11-26T19:55Z that printed a mode, 32
were `tests: mode full (selection n of m files)` at shares of 0.77 to 0.90, and none selected one test file or more. The
cause is ADR-0692 decision 1: a covered changed file also selects every test that names "its path or its folder", and the
name index holds `scripts/agk/` in 354 test files and `scripts/agk` in 330, so any changed script selects about 450 of
662 files and `full_when_share` (0.5) makes the run full. On main df7f8873, `test_plan.py` prints 555, 578, 508 and 504
selected files for the heads 0290d9a9, 25f12348, 6f8c2c6c and a512ebb7. A second, smaller widening is the one-level
importer expansion of ADR-0393 at a widely imported module (`scripts/agk/config.py`: 35 importers, 254 tests by
importers on 0290d9a9).

## Decision

1. **Exact naming for a covered file** (`scripts/agk/impact.py`, `select`, `covered_naming`). Under `balanced`, a changed
   file that an entry covers (and that is not documentation, not a test file and matches no `always_full` glob) also
   selects the tests whose name index holds its exact path, which includes the joined-literal and `Path(...)` forms of
   amendment 220. Its folder words (`<folder>/` and `<folder>`) are no longer read. This supersedes the words "or its
   folder" of ADR-0692 decision 1; the rest of that decision (the reason `(names <path>)`, the change's own test files not
   added, a stale entry staying unmapped and full) stands. A file no entry covers keeps SPEC-0055 rule 6 as written
   (`tests_naming`, path or folder), and `uncovered` and `check_kit_tests.py` read the index as before.
2. **`[testing] hub_importers`** (new, optional; `impact.KEYS`, `config.TABLE_KEYS["testing"]`). A whole number of at
   least 1. A changed code file with more direct importers that are not test files than the limit
   (`test_map.importers_of` at the head) is a hub: it selects its own entries' tests, the tests that name it, the test
   files that import it directly and `whole_tests`, and not the map tests of its importer scripts. The plan prints
   `selected: <file> -> <k> tests (hub: <n> importers, importers not expanded; setting: testing.hub_importers)` in place
   of its `(<j> by importers)` line. A file at exactly the limit is not a hub. Without the key the expansion is as before,
   line for line. `0`, a negative number, a boolean, a float or a string is refused before anything runs with
   `hub_importers must be a whole number of at least 1 (setting: testing.hub_importers)`, never the value.
3. **What does not change.** `thorough` is full and reads neither rule; `fast` reads no names and reads the limit;
   `always_full` wins over both; `full_when_share`, `local_full`, `whole_tests`, `pre_merge_tests`, `links`, `pr_tests`,
   `workers` and `parallel_command` are unchanged, and `map_source = "generated"` entries are read as curated ones. A push
   to `main`, `merge_group`, any event other than `pull_request`, a release pull request, a base that does not resolve, an
   unmapped file no test names and a selected file in no `[proof]` area still run the full suite. No workflow, ruleset,
   required check, `agk.mk`, `kit/agk-kit.mk` or `project_tests.py` changes. `execution = "local"`, solo and team review,
   personal mode and the plugin layout read the same `impact.select`.
4. **The class stays closed.** `tests/kit_dev/test_intelligent_testing.py` asserts on the kit's own tree that, for each
   covered `scripts/agk/*.py`, the tests that name it exactly are fewer than `full_when_share` of the kit's test files.
5. **AGK's own value.** This build ships the key absent in `agk.toml` (Q-P1-3): `hub_importers = 20` lands only on the
   owner's yes that names it.

## Consequences

After the change the four sampled heads select 306, 402, 77 and 66 files (161 for 0290d9a9 with `hub_importers = 20`), so
three of four run below the share instead of the full suite. A test that names only a covered file's folder no longer runs
in that pull request; a miss shows on the full run after the merge, which SPEC-0055 rule 10 and ADR-0393 accept, and the
assertion of decision 4 keeps a naming rule from selecting half the suite again.

## Residual

- 2026-11-27: 25f12348 stays full (402 of 662) through three uncovered files that take rule 6's folder fallback
  (Q-P1-2); exact-path-first for an uncovered file is an amendment for SPEC-0055's reviewers.
- 2026-11-27: the step time of a selected run is expected to fall about in proportion to its files `(verify)` on the
  first runs.

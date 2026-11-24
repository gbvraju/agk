# ADR-0787: A second init run reads test_dirs back from agk.toml (REQ-062)

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1899, found-bug #1898, ADR-0490 (front-end test folders in `test_dirs`), ADR-0769 (the forms of
  `test_dirs`), ADR-0785 (the same reuse for `test_patterns`), SPEC-0001 rule 14, plan #661
- Requirements: REQ-062

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #1154 (ADR-0490) made `init.py` add the front-end test folders it finds to `test_dirs` on the first run, and
`found_test_dirs` returns nothing once an `agk.toml` exists. A second run therefore rendered the template's
`test_dirs = ["tests"]`, compared it with the installed `["tests", "e2e"]` and refused with
`conflict agk.toml (path class agk.toml: differs)`, exit 1 (#1898, reproduced on main 24ce0773). SPEC-0001 rule 14
says a later run reads `installed` and `default_branch` back and renders the same values; `test_dirs` became a value
rendered from the tree and was never read back. The owner's word (2026-11-24, the steward chat, quoted as data):
"Yes".

## Decision

1. `init.existing_test_dirs(target)` returns the `test_dirs` value of the target's existing `agk.toml`, read through
   `common.load_config` (each entry one folder, ADR-0769), when it is a list of strings, else None (no file,
   unreadable, not TOML or another type; a missing key reads as the default `["tests"]`, the template's line). The render of `agk.toml` writes that
   list on the `test_dirs` line in the kit's form (`test_dirs = ` and the JSON of the list); only when it is None does it
   fall back to the first-run detection, `found_test_dirs`, unchanged.
2. A re-run does not detect again: a front-end folder made after the first run is not added (`Q-1898-2`); `adopt` is
   the merge path and doctor's warning still names the folder.
3. A line a person reformatted (single quotes, several lines, a comment, or an entry `load_config` reads in another
   form, such as `./e2e`) still compares `differs` and refuses as today; init never rewrites a person's file.
4. An older install's `pyproject.toml` `[tool.agk]` is not read for `test_dirs` (`Q-1898-1`).
5. `tests/kit/test_test_dirs_front_end.py` re-runs init on front-end trees in both layouts, and one case runs init twice
   on a tree holding every folder of `FRONT_END_TEST_DIRS` and test files of each kind, asserting the second run plans
   no `create` or `conflict`, so a later value rendered from the tree but not read back fails there.

## Consequences

A person or the steward can re-run init on a front-end project and it exits 0 with `unchanged agk.toml`, in the
installed and the clean layout. A first run, and a re-run on a project without front-end folders, are unchanged.

## Residual

- 2026-11-24: a re-run never adds a folder made later (`Q-1898-2`); a person adds it, or runs adopt.

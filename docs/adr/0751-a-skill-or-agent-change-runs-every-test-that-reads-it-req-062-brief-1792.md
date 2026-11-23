# ADR-0751: A skill or agent change runs every kit test that reads it, path built in parts or Markdown only (REQ-062)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1792, SPEC-0055 rule 6, ADR-0359, ADR-0692, ADR-0650, amendment 186, amendment 220, plan #661
- Requirements: REQ-062

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

The default branch was red from 00:57Z to 01:51Z on 2026-11-23 after #1773 changed `skills/upgrade/SKILL.md`:
`tests/kit/test_upgrade_adr.py` reads that file as `ROOT / "skills" / "upgrade" / "SKILL.md"` and failed, but the pull
request's selection (`pr_tests = "selected"`) did not run it. Three causes: the `skills/**` map entry did not list it;
`impact.name_index` indexed only path-like words, so a path built in parts named nothing; and `impact.is_doc` read every
`*.md` file as documentation, so a change of only shipped Markdown selected nothing at all. The owner's word
(2026-11-23, the steward chat, quoted as data): "Yes, brief the skills test-map gap".

## Decision

1. A path built in parts is a name. `impact.name_index` also indexes each path that `impact.joined_paths` reads from a
   test file: a run of two or more quoted literals joined by `/` (the expression before the run is dropped), and a
   `Path`, `PurePosixPath`, `PurePath` or `os.path.join` call whose arguments are all quoted literals; the parts are
   joined with `/`. A part holding `*`, `?` or `{` (a glob or a formatted field) ends the path at the folder before it.
   The path and its folders join the index as a word does, so both naming rules (SPEC-0055 rule 6, ADR-0692) use them
   unchanged. It only adds names, so it only adds tests.
2. A shipped Markdown file is not documentation. `impact.doc_reader(root, head)` reads a file under `docs/` as
   documentation, and a `*.md` file elsewhere only when no `[[testing.map]]` entry covers it and no class of
   `config/protected-paths.txt` at the head holds it. `select` and `uncovered` read it; `is_doc` itself, which
   `smoke.py` and `test_map.py` read, is unchanged. A change under `docs/` only still selects nothing (Q-1548-3).
3. The class stays closed. `tests/kit/test_impact_named_joins.py` runs the measure on the kit's own tree: every tracked
   file that is not documentation by decision 2 and that a test reads by a literal join selects that test on a change
   of that file alone, or the selection is full; it fails naming the file, the test and SPEC-0055 rule 6.
4. No setting is added. Under `fast` decision 1 does not apply (an unmapped file is only listed, as today) but decision
   2 does; `thorough`, `always_full` and every other `[testing]` key are read as today.

## Consequences

A change of a skill, an agent, a rule file or any file a test reads by a join runs those tests on its own pull
request. A protected or mapped `*.md` change that no test names and no entry covers now makes a `balanced` selection
full, as any other unmapped file does: on the kit's tree that is 114 Markdown fixtures under `tests/kit/fixtures/`,
whose JSON neighbours in the same folders (252) already did.

## Residual

- 2026-11-23: the importer step and a join whose first part is a variable (`FIXTURES / "facts"`) still name nothing
  beyond their literals; decision 3's test leaves the importer step out, so each pair must be named.

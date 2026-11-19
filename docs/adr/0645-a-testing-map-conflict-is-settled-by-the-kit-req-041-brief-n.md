# ADR-0645: A testing-map conflict in agk.toml is settled by the kit, not a person (REQ-041)

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: SPEC-0034, amendment 184, brief #1531, #1521, #1523, ADR-0509, plan #661
- Requirements: REQ-041

Protected classes the builds of this decision change: `scripts/agk/`, `tests/kit/`, `agk.toml`, `config/`, `kit/`.
This pull request changes none of them.

## Context

Two builds that each append a test to the same `[[testing.map]]` `tests` list of `agk.toml` conflict on the same lines,
and SPEC-0034 rule 7 (c) and session rule 15 let a builder settle only an appended line in a shared-mechanical file
(`merge=union` in `.gitattributes`, and `changelog.d/`), a regenerated file and a renumbered id. So the builder posts
`conflict needs a person: agk.toml` and waits: #1523 on 2026-11-18 and #1521 on 2026-11-19 each waited for
`Maintainer answer: the agk.toml conflict is mechanical; keep both lines`. Of the 200 commits before 6f7288da, 102
changed `agk.toml` and 91 changed lines of its map (146 entries). A textual `merge=union` cannot serve a settings file:
it keeps both sides of any line, including a changed setting. Projects meet the same conflict in their own map,
`[[testing.map]]` or the inline `map = [ ... ]` of `kit/templates/agk.toml`, since builder.txt asks every builder to add
its new test file there.

## Decision

1. Option (C) of amendment 184 is chosen: one kit subcommand of `session.py`, beside `push-check`, settles a conflict of
   `agk.toml` whose only differences are in the `[testing] map`, after `git merge` of the default branch. It reads the
   three index versions, reuses `impact.py` `_map_split`, and writes the merge only when the rest of the file merges as
   one side changed it and each `code`'s tests are the base's plus both sides' additions less both sides' removals;
   every other shape, and any doubt, refuses with `conflict needs a person: agk.toml (<reason>)` and writes nothing.
2. SPEC-0034 rule 7 (c) and session rule 15 name this as a fourth mechanical conflict. Session rule 14's
   shared-mechanical list is unchanged: the map is not a shared-mechanical file, so `overlap`, `shared_patterns` and
   `push-check` are unchanged.
3. Not chosen: (A) one file per entry (still conflicts within an entry, changes every reader), (B) a merge driver (needs
   git config that no committed file sets, silent fallback, ignored by the forge's check), (D) a generated map (0 of the
   kit's 126 script entries) and (E) a sorted one-test-per-line reformat (conflicts with every open pull request).
4. The work is two builds, each filed by the `brief` skill: (a) the resolver and its tests, (b) session rule 15, the
   builder template line and the guide's conflict paragraph.

## Consequences

A builder settles the observed conflict alone, in the kit and in every project, local and cloud, with no setup. A lost
pair would silently skip a test under `pr_tests = "selected"`, so the check refuses on any doubt and the person keeps
every other conflict. In local mode the head still moves, so the evidence and the accept are taken again. A builder
build that cites this ADR with `Covered-by:` once it is Accepted may change only the classes named above.

## Residual

- 2026-11-19: `[testing] always_full`, `pre_merge_tests`, `docs/guides/reference.md`, `kit/manifest.json` and the
  append-only `docs/runs/flakes.md` and `docs/design/signoffs.md` are not covered; each waits for the owner's word
  (due 2026-12-31).

# ADR-0101: the vision step (REQ-036 part b1, SPEC-0029 rule 4)

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0097, ADR-0099
- Requirements: REQ-036

Protected classes: `kit/`, `scripts/agk/`, `skills/`, `tests/kit_dev/`

## Context

SPEC-0029 (Approved, #166) splits its build into (a) engines and doctor (ADR-0099, #168), (b) vision and stack, and (c) design, and rule 9 splits a part at about 600 changed lines of code and tests. Part (b) measured about 400 lines of
code, templates and skills and about 450 of tests, so it is split again: (b1) the vision, here, and (b2) the stack, a separate pull request after this one is merged. The tests were written first
(`tests/kit_dev/test_engines_vision.py`; on unchanged `main` with the new files taken away, for the whole of part (b): 46 failed, 1 passed, the one being the six-topic charter that `/agk:start` already accepts).
This pull request branches from the default branch and does not stack on the unmerged build of lane A (#169); the number 0100 is that build's, so this ADR takes 0101.

## Decision

1. **The script** (kit-only): `scripts/agk/engines.py` with `questions`, `vision-write` and `vision-check`. It reads and writes files only; no network, no model. An engine (a skill named in `[engines]`, ADR-0099) only drafts; the
   script writes the draft through the kit's template and the check refuses what does not fit. The script decides nothing.
2. **The vision** (rule 4): `vision-write --idea-file F [--draft-file D]` writes `constitution/vision.md` with the owner's idea, byte for byte (surrounding blank lines trimmed), as the first section `## The idea`, between
   `<!-- agk-idea sha256:<digest> -->` and `<!-- /agk-idea -->`; the four sections of `/agk:start` follow, from the draft (which must hold the four headings in order and no placeholder or idea marker) or from
   `kit/templates/vision-sections.md` with `TODO(owner)` marks. The idea is refused when empty, over 1,500 characters (the limit of `/agk:start`) or when it holds a marker; an existing idea is never overwritten, and neither is a vision that holds content: the file must be absent or still hold the installed placeholder (`TODO(maintainers)`, the test `check-start` uses).
   `vision-check` fails, naming the rule and never quoting the idea, a vision whose first section is not the idea between its markers, whose digest differs, that has something before it, or that still holds a `TODO(owner)` mark; a
   vision without the idea section passes as before. `playbook.py check-start` runs the same check.
3. **The ten questions** (rule 4): `questions` prints the ten discovery topics in order: the six of `/agk:start` and `devices`, `accessibility`, `languages` and `brand`. `playbook.py check-start` still accepts the six alone, and
   accepts ten; when the vision has the idea section it requires all ten, each answered or `not known yet` with its Slice bullet. A charter written before this change is not checked again.
4. **The skill**: `skills/vision/SKILL.md` (user-only; it writes files and never commits) says that the engine named in `[engines]` or the template drafts, that an engine never decides and never edits a protected file, and which
   checks to run. `docs/guides/reference.md` lists the command.
5. **No default engine, no version bump** (flow mode, SPEC-0028): one line under Unreleased in `CHANGELOG.md`; `engines.py`, the skill and the template are plugin files, so no installed file changes (the table of hashes is refreshed by the script).

## Consequences

- An owner with a brief idea gets a vision that keeps the idea verbatim and a charter that records ten answers.
- `check-start` imports one more module; a project without the idea section sees no change.

## Residual

- 2026-10-24: a vision whose idea markers are removed passes `vision-check` as a vision without the idea section, and the charter is then checked for six topics only; review catches it, because the diff shows `constitution/vision.md` changing (due 2026-12-31).
- 2026-10-24: `vision-check` runs from the skill and from `check-start`; it is not a governance step, so a later change of the idea outside that flow is caught by review (due 2026-12-31).
- 2026-10-24: the digest detects a changed idea, not a rewritten digest; a person who edits both is seen in the diff of the pull request (due 2026-12-31).

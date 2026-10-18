# ADR-0037: intake, part 1 of 3: `intake.py ids` and `intake.py stub` (SPEC-0012 rules 1, 2 and 8)

- Status: Proposed
- Date: 2026-10-18
- Deciders: maintainers
- Related: ADR-0019, ADR-0021, ADR-0036
- Requirements: REQ-019

Protected classes: `scripts/agk/`, `tests/kit_dev/`

## Context

SPEC-0012 (Approved) measured, when built, at about 1,250 changed lines of code and tests, over the brief's limit of about 600. It is built in three
pull requests, each one a reviewable unit that changes no installed file until the third:

1. **This one (REQ-019 AC1, part):** the kit-only script `scripts/agk/intake.py` with `ids` and `stub`, and its tests.
2. **Part 2:** the checks C1 to C9 (`intake.py check`) and the test that a draft on a branch is not a fact (rule 14).
3. **Part 3:** `intake.py next-steps`, the `/agk:spec "<sentence>"` form of the skill, the `## Open questions` section of the spec template, the
   issue form's one-sentence hint, the SPEC-0009 `open_in` amendment and the SPEC-0005 row (`proposed-spec-amendments-14.md`, items 1 and 2),
   the end-to-end test, and the kit bump.

Nothing in this part is installed in a target: `intake.py` is kit-only (like `new_spec.py`), so the kit version, the hashes and the plugin version
do not change, and no skill calls the script yet.

## Decision

1. **`python3 scripts/agk/intake.py ids --sentence TEXT [--ref REF] [--root DIR]`** prints one JSON object `{"req", "spec", "adr", "slug"}` and
   writes nothing (rule 2). The three numbers are the next free ones in the tree of `origin/<default branch>` (`default_branch` of `agk.toml`),
   read with `git show` and `git ls-tree`, never from the work tree; the script does not fetch (the skill does, in part 3). `--ref` overrides the
   ref for the tests. When the ref does not resolve the script stops and names the setting; it never guesses an id. The slug follows the rule of
   `new_spec.py` (lower case, hyphens, at most 60 characters).
2. **The sentence is validated first** (rule 1): empty, longer than 300 characters, with a line break, or with more than one sentence is refused
   with `refused: rule 1: ...` and nothing is written. The message names the rule and never the sentence.
3. **`python3 scripts/agk/intake.py stub --req REQ-nnn --title TEXT --sentence TEXT [--date D]`** writes the ADR file from a fixed text (rule 8):
   `Proposed`, the date from `date -u` (or `--date`), `Requirements:`, a `Protected classes:` line naming `docs/requirements.md`, the sentence
   quoted as data, and a Decision that says merging approves the requirement as a proposal and not the spec. It refuses a `--req` that is not the
   next free one, a title over 80 characters or with a semicolon, and an existing file. The file passes `check_adrs.validate`.
4. **Tests** (`tests/kit_dev/test_intake.py`, no model): gaps and an unordered highest number; leading zeros; a spec and an ADR with the same number
   are independent; an empty requirements file starts at 1; the base, not the work tree, gives the ids; `origin/<default>` is the default ref and a
   missing one refuses; the sentence limits (empty, 301, exactly 300, two sentences, a line break); the slug limit; the stub passes `check_adrs`,
   names the class, takes the date, quotes the sentence, refuses a wrong id, a bad title and an existing file.
5. **No installed file, no skill, no spec text changes in this part.** The amendments of `proposed-spec-amendments-14.md` are applied by the ADR
   of part 3.

## Consequences

- The ids and the stub exist and are tested before anything calls them; the model's surface in the later parts is only the text rule 9 allows.
- Until part 3 merges, `/agk:spec` has only the forms of SPEC-0005.

## Questions

| Q | Question | Reading taken |
| --- | --- | --- |
| Q-K4-173 | How is "one sentence" tested? Rule 1 does not say. | A sentence end (`.`, `!` or `?`, one or more) followed by whitespace and more text counts as a second sentence, so `e.g. a list` is refused and `3.5` is not. Conservative: a person can reword; a second sentence cannot slip through. |

## Residual

- 2026-10-18: the one-sentence test is a pattern on sentence ends; an abbreviation inside a sentence is refused and must be reworded (due 2026-12-31).

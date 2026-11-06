# ADR-0310: A rule budget that only shrinks, and fix-list items tagged by rule (REQ-037, brief 647)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0247, ADR-0294, SPEC-0021, SPEC-0023, SPEC-0045
- Requirements: REQ-037

Protected classes: `config/`, `.claude/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

The owner asked whether the number of rules and files an agent reads is a risk for AGK, and how
slow drift is stopped (brief #647, tracker #630 item 12). On the default branch on 2026-11-06 a
builder reads about 5,200 words before its brief, and `.claude/agents/conductor.md` alone is about
4,500 words. Since 2026-11-04 more verdicts carried a fix list than cleared, most of them for
format misses, the kind of rule an overloaded agent drops first. Nothing counted which rules were
dropped, and nothing stopped the files from growing. This is build (a) of the brief; build (b),
the consolidation of `config/session-rules.md`, follows after a week of counts.

## Decision

1. **The budget (answer 1).** `config/rule-budget.txt` records, for each instruction file an
   agent reads, `<path> <words> <rule lines>`: `CLAUDE.md`, `constitution/principles.md`,
   `config/core-rules.md`, `config/session-rules.md` (the files `launch.py prompts` names and the
   lean list of SPEC-0045 rule 7), every file under `.claude/agents/`, and
   `config/review-checklist.md`. Words are the whitespace-separated words of the whole file; a
   rule line is a numbered (`1.`) or bulleted (`-`, `*`, `+`) line outside the front matter and
   outside fenced code. `python3 scripts/agk/rules.py budget` prints the counts and `--check`
   compares them; the kit test `tests/kit/test_rule_budget.py` fails when a count rises above its
   line ("a rule was added: retire one, or make it a check, in the same pull request"; for words,
   cut words or move the how-to into a guide), when a line is above its file ("lower the
   baseline"), when a listed file is gone and when an agent file is not listed. The baseline is
   under `config/`, a protected class, so raising it needs a decision record.
2. **The tag (answer 2).** Item 8 of the review protocol, identical in
   `.claude/agents/architect.md`, `architect-review.md`, `conductor.md` and `shadow.md`, asks that
   each numbered item of a fix list ends with `(rule: <file> <n>)` or `(rule: none)`.
   `check_final_clearance.py`, the check that reads the latest verdict of a pull request, warns on
   a numbered item of the latest `Verdict: fix list <sha>` that has no tag, and fails on it from the
   date in the top-level setting `rule_tags_from` of `agk.toml` (this repository: `2026-12-06`, 30
   days from this build). Without the setting it only warns, so no installed project is failed by
   it. A value that is not a `YYYY-MM-DD` date is refused naming the setting.
3. **The count (answer 2).** `python3 scripts/agk/rules.py dropped --since DATE` reads, GET only,
   the pull requests updated since DATE that are open or merged, and their comments, and counts
   the numbered items of the fix lists by a listed verdict author posted since DATE: one line per
   rule tag, newest first, then the untagged items as references (pull request, comment id, item
   number) and the pull requests whose comments could not be read. It prints no comment text. An
   unreadable pull request list is `unknown`, never 0. `rules.py` is kit-only: it is not installed
   in targets (listed in `KIT_ONLY` of `tests/kit_dev/test_kit_manifest.py`).
4. **No amendment (answer 3).** The drift audit (SPEC-0004) reads git and files only, with no
   network and no `gh`; the per-rule count needs the pull request comments. Carrying it there would
   change the audit's sources, so the command alone is this build and amendment 126 is not used.
5. **Unchanged.** `constitution/` (the owner's hold list), the meaning of every session rule, the
   questions of `config/review-checklist.md` (it changes only from a catch-log row), and the
   reading of a covered fix list (SPEC-0021): a fix list with numbered items is still never
   covered.

## Consequences

A rule added to any instruction file shows up as a baseline change in a protected file that a
reviewer must accept; a cut file lowers its line in the same pull request. Every fix-list item
names its rule, so a week of `rules.py dropped` shows which rules agents drop, and build (b) cuts
the rule set by that evidence. From `rule_tags_from` on, an untagged fix list leaves the builder's
head red until the conductor posts a tagged one.

## Residual

- 2026-11-06: the word budget is exact, so two pull requests that each change an instruction file
  conflict on `config/rule-budget.txt`; the later one merges the default branch and recounts with
  `rules.py budget` (due 2026-12-31).

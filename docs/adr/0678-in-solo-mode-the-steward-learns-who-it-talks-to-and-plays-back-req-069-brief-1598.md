# ADR-0678: In solo mode the steward learns who it talks to and plays back what it understood

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1598, SPEC-0062, SPEC-0059, ADR-0557, ADR-0582, ADR-0310, plan #661
- Requirements: REQ-069

## Context

SPEC-0062 (Approved) rule 18 build (a) builds rules 3 to 7 and 10: in solo mode the steward assumes nothing about the
product, first learns who it talks to and what they want to build, uses their words, explains a kit term once, plays
back what it understood before a stage's skill runs, follows the person's pace and stays on the product. On the default
branch `steward.py record --kind Person` is refused as not a memory kind, the role file asks no first question and has
no play-back, and `steward_voice.py check` refuses every kit-term form outright, with no way to explain one.

## Decision

1. `steward.py` gains the memory kind `Person`, recorded as `Person: <business|technical>: <their words>` and ending
   `Who: ProductOwner` (SPEC-0062 rules 4 and 15); any other form is refused, naming the rule, never the text. In solo
   mode (`review_mode = "solo"`), a `start` whose memory holds no `Person:` entry prints `ask:` with rule 4's one
   question. In team mode the start is SPEC-0059's exactly (rule 2). Personal mode writes the entry to the sidecar.
2. The planted kit-term list is one section, `## Kit terms`, of `docs/guides/steward-voice.md`: each line is a term and
   its one-sentence explanation (brief question 1). `steward_voice.py check` reads it: a listed term passes only with
   its sentence in the sentence that first names it, or when the memory already holds its `Term: kit:` entry; a term
   explained again after that fails as explained twice. The other kit-term forms of ADR-0582 rule 8 still fail.
   `steward_voice.py explained FILE` records each term a reply explains for the first time as one
   `Term: kit: <term>: <sentence>` entry, so no term is recorded or explained twice.
3. `steward_voice.py playback FILE --reply TEXT` is the gate before a stage's skill: exit 0 (`go on`) only when the
   play-back is three sentences or fewer and the reply is a plain yes in rule 14's reading (an explicit approval with
   no condition, change or question); exit 1 (`play back again`) on anything else, and nothing is written. A play-back
   over three sentences is refused (exit 2).
4. `steward_voice.py offtopic --product TEXT` prints rule 10's one polite line back to the product in the person's words.
5. The guide gains a `## Solo mode` section with rules 3 to 7 and 10 (day 0, understood first, the play-back, no kit
   term, the person's pace with an early result shown only when asked and recorded as a `Decision:`, the thinking
   partner, only the product). The role file gains one `Solo.` paragraph that points at it. The rule budget holds
   (ADR-0310): `.claude/agents/steward.md` stays at 943 words, with the words of the new paragraph taken from text
   that restates what the scripts print.

Protected path classes changed: `.claude/` (`agents/steward.md`), `scripts/agk/` (`steward.py`, `steward_voice.py`),
`tests/kit/` (`test_steward_person.py`) and `agk.toml` (the `[testing]` map entries of `steward.py` and
`steward_voice.py`).

## Consequences

A solo steward cannot start a stage without a confirmed play-back if it follows its role file, and its memory shows who
the person is in their own words. The check now lets a reply explain a listed term once, which ADR-0582 rule 8 refused
before. The yes reading here is the narrow one of SPEC-0062 rule 14; build (d) owns the approval that a yes posts.
The steward running the gate is the role file's instruction, not a guard: a stage skill run without `playback` is not
refused.

## Residual

- 2026-11-20: a kit term missing from the planted list is not caught, as SPEC-0062's residual says (due 2027-03-31).
- 2026-11-20: whether the steward runs `playback` before each stage is not machine-checked; a guard for it is a later
  brief (due 2027-03-31).

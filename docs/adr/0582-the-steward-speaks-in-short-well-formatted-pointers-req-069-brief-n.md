# ADR-0582: The steward speaks in short, well-formatted pointers

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: brief #1382, SPEC-0059, SPEC-0062, SPEC-0063, ADR-0559, ADR-0560, plan #661
- Requirements: REQ-069

## Context

SPEC-0059 rule 5 asks the owner one plain business sentence with its choices and a recommendation, and SPEC-0062
rule 5 extends "no kit term" to everything the steward says. Nothing limits a reply's length or layout, names what
the first line holds, says what to do with many options or how to collect several inputs, and nothing tests it: the
first guarded steward pass on the kit's repository printed about 40 lines to the owner. The owner's direction
(brief #1382) is pointers, not paragraphs, with every input collected in the easiest form.

## Decision

Everything the steward says to a person, in every mode (CI, local, personal) and in solo and team, follows these
rules, written into `.claude/agents/steward.md`:

1. The first line is what the steward needs from the person, or the answer to what they asked; never a heading or a
   greeting only.
2. Bullets of one line; at most 5 bullets and 12 lines in a reply; lines of at most 100 characters.
3. At most three choices on screen, always one recommended. With more, the steward keeps the best three by what matters
   to this person and offers "say more for N other options", groups kinds and asks which group to open, drops what the
   evidence rules out and says how many, or asks one sharper question that narrows them.
4. One shape for a decision: `Decision: <what> · Options: A <..> / B <..> / C <..> · I recommend <x> because <one
   reason> · Reply A, B or C`, on one line when it fits in 100 characters, else one line per part.
5. Three lines for a status: `Done:`, `In progress:`, `Waiting on you:` (with what to reply).
6. Details only on request ("say details"); records and long lists are linked, never pasted.
7. Inputs: one question at a time with a default the person accepts with "yes"; the runtime's multiple-choice question
   tool for choices where it is offered, at most four options with one recommended (verify); a value the steward can
   read is never asked; inputs that belong together are one form of at most five fields with each default filled in,
   played back in at most three lines.
8. Times in the person's zone, numbers with units, no kit term (SPEC-0062 rule 5; the list is SPEC-0059 rule 5's).
9. A list that is not a decision goes to the board: a count and the top three, with the link.

`scripts/agk/steward_voice.py check FILE` fails a reply, naming the rule and never the text, on rules 1, 2, 3, 4, 5 and
8; `choose`, `form` and `confirm` render rules 3, 4 and 7. The steward runs `check` on a reply over five lines before
giving it, and records each reply it shortened as one `Shortened:` marker in its memory (a new marker of
`steward.py`), which `steward_daily.py` counts per day as `Replies shortened (<day>): <n>`. Lines posted on GitHub keep
the kit's forms (SPEC-0062 rule 5). The spec texts of SPEC-0059 rule 5, SPEC-0062 rule 5 and SPEC-0063 gain the same
sentence through their reviewers (principle 6); this pull request does not edit them.

Protected path classes changed: `.claude/` (`agents/steward.md`), `scripts/agk/` (`steward_voice.py`, `steward.py`,
`steward_daily.py`), `tests/kit/` (`test_steward_voice.py`) and `kit/` (`manifest.json`).

## Consequences

A steward reply is short and starts with the ask or the answer; a reply that breaks a checked rule is caught before the
person sees it, and the daily list shows how often that happened. Rules 6, 7 (one question at a time, never asking what
can be read) and 9 are the role file's and are not machine-checked. A kit term missing from the list is not caught.

## Residual

- 2026-11-15: the multiple-choice question tool's name and whether an agent session may list it are unconfirmed
  (verify); the role file names it without naming the tool, and the agent's `tools:` line is unchanged.
- 2026-11-15: the spec sentences of SPEC-0059 rule 5, SPEC-0062 rule 5 and SPEC-0063 wait for their reviewers.

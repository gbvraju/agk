# ADR-0520: Planning keeps open questions few and its render repeatable

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0043 rules 6, 7 and 25, amendment 179, ADR-0461, ADR-0465, ADR-0473, ADR-0508, brief #1221, plan #661
- Requirements: REQ-050

## Context

In a customer trial `/agk:plan-intake` produced 2,043 open questions, 2,020 of them cross-reference gaps of the same
kind (`requirements <key>: cross-reference <n> of its statement names no one source heading`, written by the OpenSpec
reader, ADR-0473). `publish` files one business question issue per open question (ADR-0508), so business would have
received 2,043 issues; they were grouped by hand into 26. `plan_intake.py render` writes new files only (SPEC-0043
rule 7, ADR-0461), so a second pass after a fix to the proposals had to be worked around by hand.

## Decision

1. Open questions of one kind and one area are one question for business. The kind of a question written
   `<section> <key>: <text>` (`requirements`, `personas`, `milestones`, `briefs`, `components`) is its section and
   `<text>`; of any other question, its whole text. Its area is the feature area of `areas` that holds the requirement
   it names, else the file of its first source. A group of two or more is keyed by its first question's key, asks
   `<section> <keys> (area <area>): <text>`, cites every source of its members once and blocks the keys it holds
   first, then every key a member blocked (ADR-0508). A kind asked once is unchanged. `render` writes the groups into
   `Questions for business` and prints them under `Open questions for the person`, so `publish` files one issue per
   group.
2. A cross-reference gap is a note of its requirement, never a question: the OpenSpec reader writes it into the
   requirement's new optional `notes` list (rule 4 types it as a list), and an open question of that form naming a
   requirement of the proposals is moved to that requirement's notes. `render` writes each note as a `Note:` line
   of the requirement's block in `docs/plan/requirements-proposed.md`, after `Story:`, `Statement:` and `Changing:`.
3. `validate` prints `warning: <n> open questions, above [plan] max_questions (<limit>)` before `ok proposals` when the
   questions for business (the groups and the unsettled conflicts, what `publish` would file) are more than
   `max_questions` of the `[plan]` table of `agk.toml`, 60 when absent. It is a warning: the exit stays 0. The setting
   is a positive whole number; any other value is a refusal naming `[plan] max_questions` (`common.plan_settings`,
   ADR-0465).
4. `render` keeps a digest list beside the plan, `docs/plan/render-digests.json`: `files`, each file it wrote under
   `docs/plan/` to the SHA-256 digest of its bytes, and `specs`, each feature area's name to the Draft spec it made. A
   first render refuses over an existing list as over any of its files.
5. `render --again` rewrites a file only when the list holds it and its bytes still have the listed digest (printed
   `rewrote` or, when the bytes would not change, `unchanged`), creates a file that does not exist (`created`), and
   leaves as it is, naming it, a file a person edited (`kept <path>: edited since the last render`) or one the list does
   not hold (`kept <path>: not written by render`). A feature area already listed keeps its Draft spec as it is
   (`kept <path>: a Draft spec is written once`), since a spec is the person's from its first render; an area not yet
   listed gets a new one. Without a readable list, `--again` refuses and writes nothing. Kept files keep their old
   digest, so a later pass still keeps them.
6. A brief key repeated across milestones stays refused by `validate` (and so by `render`) and by `publish`, as on the
   default branch; `validate`'s line now says where: `rule 4: briefs <key>: the key is repeated in M1, M2`, every
   milestone that holds the key (the brief's correction, `Q-1221-2`, reading (b)). Allowing such a key and renaming it
   `M<n>-<key>` on render is not decided here: it is the owner's to choose.

## Consequences

A large source set asks business few, readable questions, and a second pass after a fix needs no hand work, while a
person's edit is never overwritten. SPEC-0043 rule 7 says a later render refuses to overwrite, rule 25 files one issue
per open question and amendment 166 makes a cross-reference gap a question: the lines that change them are proposed in
`docs/runs/proposed-spec-amendments-179.md` (`Q-1221-1`, answered: amendment 179), without editing the spec. Protected path classes changed: `scripts/agk/` (`plan_intake.py`; `common.py`, whose `plan_settings`
accepts `max_questions`) and `tests/kit/` (`test_plan_intake_questions.py` new; `test_plan_render.py`, whose list of
written files gains the digest list; `test_plan_openspec.py`, whose two cross-reference tests now find notes, not
questions). No workflow, ruleset, `.claude/` or `skills/` change.

## Residual

- 2026-11-14: SPEC-0043 rules 6, 7 and 25 keep their present text until the maintainers apply amendment 179
  (`docs/runs/proposed-spec-amendments-179.md`), due 2026-11-30.

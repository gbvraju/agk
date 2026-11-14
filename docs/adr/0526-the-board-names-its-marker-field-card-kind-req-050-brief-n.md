# ADR-0526: The board names its marker field Card kind

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0506, ADR-0507, ADR-0508, brief #1240, plan #661
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `skills/`

## Context

ADR-0508 decision 5 has `board.py` add a single-select field named `Type` (Work, Question) once a business question is
on the board. GitHub Projects now ship a built-in `Type` field (issue types), and `gh project field-create --name Type`
is refused with `Name cannot have a reserved value, Name has already been taken`. The owner's run of `/agk:board --yes`
on a project with 652 briefs and 38 questions stopped there, before any card was added, and a rerun stopped at the same
place. The failure printed only the command, not gh's message.

## Decision

1. The marker field is named `Card kind`, with the options Work and Question unchanged; the views text, the planning
   guide and the board skill say `Card kind`. This replaces the field name of ADR-0508 decision 5; the rest of that
   decision stands.
2. A board that already has a field `Type` with the options Work and Question (an older board) keeps it as its marker
   field, read and written as before, and gets no `Card kind`. A field named `Type` of any other kind (the built-in
   one, listed by gh or not) is never created, renamed or written.
3. A field creation that gh refuses prints `failed: <the command>` and then
   `board: the field <name> was not added; gh said: <gh's message>`, exit 1, and the run stops before adding cards.
4. A rerun on a board that has the fields and no cards adds the missing field and every card, each once.

## Consequences

`/agk:board --yes` finishes on a project with the built-in `Type` field. A template board that already carries a
`Card kind` field is used as it is. A board an owner built by hand with a field `Type` of other options gets `Card
kind` beside it, and its `Type` is left alone.

## Residual

- 2026-11-14: how `gh project field-list --format json` lists the built-in `Type` field (listed or not, and its
  `type` value) is not read here, since a cloud session cannot reach GitHub Projects; the tests cover both (verify on
  the owner's machine; due 2027-01-31).

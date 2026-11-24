# ADR-0733: The steward files a brief on the owner's named yes, and never files the same draft twice (REQ-066)

- Status: Accepted
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1753, brief #1715, ADR-0714, SPEC-0059, SPEC-0062
- Requirements: REQ-066

Protected classes: `scripts/agk/`, `tests/kit/`, `.claude/`

## Context

`steward_owner.py file-brief` counted the person's words as a yes only through `steward_voice.is_yes`, a full match of a
short list (`yes`, `yes, go ahead`, `approved`, ...). The steward's owner lists offer a named line, such as `Yes, file the
gate-runner test map brief`; on 2026-11-22 those exact words printed `not a yes: nothing filed`. And `file-brief` posted
without looking at the open briefs, so a second yes filed the same draft as a second brief (#4 and #5 in a sample
project).

## Decision

1. `file-brief` takes `--name <name>`, the short name the steward offered the owner for this draft. With `--said` and
   `--name`, the words also count as a yes when, ignoring case, one end period and runs of spaces, they are exactly
   `yes, file the <name> brief`, `yes, file <name>`, `yes, brief the <name>` or `yes, brief <name>` (the comma optional).
   The condition backstop (`?`, `but`, `if`, `except`, `unless`, `change`, `not`, `later`) still refuses first. Without
   `--name` only the plain yes counts. `is_yes`, `approve` and `relay` are unchanged: an approval stays a plain yes.
2. `--name` is one line of 1 to 80 characters with no backquote; any other value, or `--name` without `--said`, is
   refused naming `--name`, never the value. A named yes whose name differs from `--name` is not a yes.
3. Before posting, `file-brief` reads the open briefs (`issues?labels=agk-brief&state=open`, page by page, GET only) and
   refuses when an open brief's title equals the new title (ignoring case and runs of spaces), or its body without its
   `Owner said` line equals the draft's: `refused: #<n> is an open brief with this title or body; nothing filed (setting:
   --title)`. Nothing is recorded on a refusal; an unreadable listing fails closed (`error: the open briefs cannot be
   read`, exit 4). The check holds on the `auto_file` path too. Personal mode prints the brief as before and reads
   nothing.
4. The steward's role file names `file-brief --name`, inside its word budget.

## Consequences

The owner's named yes files once; a second filing of an open brief names it and files nothing. One more GET listing per
filing in GitHub and local mode. A closed brief with the same title does not block.

## Residual

- Q-1753-1 (2026-11-22): a named line without `yes` (`file the checkout brief`) does not count, the conservative reading.
- 2026-11-22: a name holding a backstop word (`not`, `change`, ...) as a whole word is never a yes; the steward offers
  another name.

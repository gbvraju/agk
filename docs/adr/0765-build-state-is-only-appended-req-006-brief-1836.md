# ADR-0765: The build-state check fails a changed or removed row (REQ-006)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1836, ADR-0001, ADR-0111, ADR-0146, ADR-0550, ADR-0648, CM-14.4 of #1772, plan #661
- Requirements: REQ-006

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

Principle 4 says "Build-state is only appended, and only by docs commits." `check_build_state.py` (ADR-0001) checked
only the second half: a docs-only branch that rewrote a row, added a space to one, turned its lines to CRLF or removed
a row printed `ok build-state (docs-only change)`, exit 0 (CM-14.4 of #1772, reproduced on main at e13f4f53). Principle
11 says a check is changed by ADR. The owner's word (2026-11-23, the steward chat, quoted as data): "Yes, go ahead".

## Decision

1. After today's checks pass, unchanged and in today's order (path unchanged, file created, deleted, outside docs/),
   the check reads the base's bytes of `docs/build-state.md` at the merge base (`git cat-file blob`, never decoded) and
   the head's bytes from the working tree through `common.committed_bytes`, splits both into lines with their line ends
   kept, and fails unless the base's lines appear in the head in the same order, each byte-equal (one greedy pass).
   "Only appended" is read per line, not as "the base is a prefix" (Q-HC-1): the file's template puts new done rows
   before `## Decisions`, so lines may be inserted anywhere. A failure prints `FAIL build-state: docs/build-state.md is
   only appended; an existing row was changed or removed (path class: docs/build-state.md)` and exits 1, naming no
   row, line or count. A pass prints `ok build-state (rows appended)`; equal content (a mode change only) keeps
   `ok build-state (docs-only change)`.
2. Line ends and spaces count: a trailing space, a tab, CRLF for LF or LF for CRLF in the committed bytes, or a
   byte-order mark is a changed row. A working tree whose CRLF comes only from `core.autocrlf=true` is read as its
   committed bytes (ADR-0550). One exception: the base's last line with no line end matches the head's line that is
   that line plus one line end, so an honest append to such a file passes.
3. The base is today's merge base (`common.base_context`): the merge ref's first parent in CI (ADR-0111), the record's
   base locally. No new way to choose a base, no setting and no exemption is added; the half cannot be turned off.
4. A correction to a wrong old row is a new row (`| <date> | correction of <date> row: ... |`), never an edit (Q-HC-2).

Path classes changed: `scripts/agk/` (`check_build_state.py`), `tests/kit/` (`test_check_build_state.py`) and
`tests/kit_dev/` (`test_merge_ref_base.py`). The script is installed verbatim (`kit/manifest.json`), so every project
gets the stricter check on its next upgrade or plugin release; a changelog fragment says so.

## Consequences

The done log stays a record nobody rewrites, in the kit and in every project. A project whose docs commit corrected
an old row by an edit now fails `governance` and writes a correction row instead. Every change of the kit's own file
so far only added lines, so nothing the kit has done fails. A file that is not UTF-8 is compared as bytes.

## Residual

Whether an insert between two old rows should fail too is left to a later brief (Q-HC-1, 2026-11-23).

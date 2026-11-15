# ADR-0574: The Who line leaves a comment body read from a file alone

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: brief #1369, found bug #1303, ADR-0546, plan #661
- Requirements: REQ-050

## Context

ADR-0546 made every comment the kit posts end with a `Who: AGK` line: `common.who_fields` passes the `body=` field
of a comment write through `with_who` after any of `-f`, `-F`, `--field` and `--raw-field`. After `-F` or `--field`,
`gh api` reads a value that starts with `@` from a file (`@-` from standard input). Found bug #1303 showed that
`-F body=@/tmp/x.md` became `body=@/tmp/x.md` followed by the Who line, which `gh` no longer reads as a file name,
so the post would carry the literal text and not the file. Measured on main at eff2fcb (session rule 19):
`who_fields('repos/example/project/issues/5/comments', 'POST', ['-F', 'body=@/tmp/x.md'])` returns
`['-F', 'body=@/tmp/x.md\n\nWho: AGK']`. No kit poster sends a file body today; the steward, the supervisor of
SPEC-0064 and project scripts may.

## Decision

1. `common.who_fields` leaves a `body=` field whose value starts with `@` unchanged when it follows `-F` or
   `--field`. The Who line of such a post is the poster's to write into the file.
2. After `-f` or `--raw-field`, which never read a file, a value that starts with `@` is a literal at sign and still
   gains the line, as does every other `body=` value; `who_argv` follows `who_fields`.

## Consequences

A post made with `-F body=@file` posts the file. Such a post carries no Who line unless the file holds one; the line
stays a marker, not a rule (ADR-0546), so nothing refuses it. Protected path classes changed: `scripts/agk/`
(`common.py`) and `tests/kit/` (`test_who_line.py`), with one `changelog.d/` fragment.

## Residual

- 2026-11-15: a field joined to its flag (`-Fbody=@x.md`, `--field=body=@x.md`) is not read as a field by
  `who_fields`, before or after this change; no kit poster writes one.

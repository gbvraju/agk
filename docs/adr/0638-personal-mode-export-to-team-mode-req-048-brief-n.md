# ADR-0638: Personal mode exports its records to team mode on new branches, renumbered and lossless, never pushed

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: ADR-0267, SPEC-0041, brief #1508
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0041 rule 24 asks for `personal.py export --target CLONE`, a dry run that with `--write` writes the sidecar's
records on a new branch of the target, renumbered against it with statuses reset, with printed `gh issue create`
commands for open briefs, a second branch of test markers and `export-map.json`, and never a push. Rule 25 asks that
`export --check` fails unless every record is in that map as mapped or withheld. On main there was no `export`: a
developer's personal records could not reach team mode. ADR-0267 asks each build of the spec for its own ADR naming
its classes; this is build (m).

## Decision

1. `personal.py export --target CLONE [--write] [--branch NAME] [--with-notes]`. Without `--write` it prints each
   record's mapping and writes nothing. With it, it refuses a `--branch` equal to the target's default branch, a
   branch that exists and a target work tree that is not clean, each naming the option; it then makes the branch
   from the default branch (`origin/<default>` when present), writes and commits there, makes `<branch>-tests` the
   same way, and switches the target back to the branch it was on. Nothing is pushed and the clone the person works
   in is not written. The default name is `agk/personal-export`.
2. The records branch holds the `adopt.build_plan` files of action `create` when the default branch has no
   `agk.toml` with a kit `version` (a plan conflict is refused), the requirements (appended to
   `docs/requirements.md`), specs and ADRs (new files) renumbered with `intake.rewritten` in one pass from the first
   free ids: `common.next_free_ids` on the base when AGK is installed, else counted over the plan's files, since
   `next_free_ids` reads only a committed tree. Statuses reset to `planned`, `Draft` and `Proposed`. Each ends
   `confirmed by <person> in personal mode on <date>` when a terminal confirmation of rule 8
   (`reviewers.derived_only`) names it, else `drafted in personal mode, not confirmed`. Open briefs are written to
   `docs/briefs/`, decisions-log rows are appended to `docs/runs/decisions-log.md`, and `docs/runs/export-map.json`
   records every mapping.
3. The tests branch puts a `<comment> REQ-n ACm` line (`#` for the hash-comment languages, else `//`) above the first
   line naming each test of `test-map.toml`; a test it cannot find is withheld with a reason (principle 10).
4. Records are: each `### REQ-nnn` section, each numbered spec and ADR, each brief file but `TEMPLATE.md`, each
   decisions-log row, each file under `records/notes/` (field notes) and each test id of `test-map.toml`.
   `REQ-001` to `REQ-099` are AGK's own and withheld; a brief with a `- Status: done|closed|retired` line is
   withheld; field notes are withheld unless `--with-notes` (Q-S0041-11).
5. Every record text the branch would carry is scanned with `guard.scan_text` before anything is written, and a
   finding refuses the export naming the path class, never the value. The adopt plan's files are the kit's own
   bytes, checked by `kit/hashes.json`, and are not scanned: the kit's checks hold invented patterns that the scan
   flags.
6. `gh issue create --title <title> --label agk-brief --body-file docs/briefs/<name>.md` is printed for each open
   brief and never run.
7. `--write` keeps the map as `records/export-map.json` in the sidecar with one sidecar commit. `export --check`
   reads it and fails unless every record is in it as `mapped` with a target or `withheld` with a reason. The
   failure line is `export --check: failed: <n> record(s) not in export-map.json, first <id> (SPEC-0041 rule 25)`.
   A missing map fails naming its path.
8. `tests/kit/test_personal_export.py` covers each case on invented repositories and sidecars. `agk.toml` maps
   `personal.py` to it.

## Consequences

A developer can hand their personal records to the team as reviewable branches. Every confirmed record arrives
unconfirmed for the team's own review, and the map shows the team which personal record each id came from.

## Residual

- 2026-11-20: field notes have no settled place in the sidecar; this build reads `records/notes/` (Q-1508-2).
- 2026-11-20: "open brief" is read as a brief with no `- Status: done|closed|retired` line (Q-1508-3).

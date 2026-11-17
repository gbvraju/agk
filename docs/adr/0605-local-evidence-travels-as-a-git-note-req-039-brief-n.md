# ADR-0605: Local evidence travels as a git note

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1447, ADR-0208, ADR-0233, ADR-0536, ADR-0564, plan #661
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

In local mode a clearing verdict needs `Evidence check: agrees`, read by `evidence.py check --head <sha>` from the
clone's shared evidence folder, `<git common dir>/agk-evidence/<head>.json` (ADR-0536). That folder is one per clone:
a second clone answers `evidence: no record for this head in the shared evidence folder (option: --record)`, exit 3,
and `docs/guides/local-mode.md` told a builder on another machine to copy its record file to the conductor by hand
(ADR-0564). A team on several machines could not clear a member's pull request unattended.

## Decision

1. `scripts/agk/prepush.py`: `--record` with no FILE, in local mode (`execution = "local"`) and outside personal mode
   (no `[personal]` table), also stores the record file's bytes as a blob and adds it, unchanged, as the note of the
   head under `refs/notes/agk-evidence`. `guard.scan_text` reads the bytes first; a finding writes no note and prints
   one line naming the path class `refs/notes/agk-evidence`, never the value. A note that git cannot write prints one
   line naming the same setting. Neither changes the exit code or the record. On success prepush prints the command
   that sends it: `python3 scripts/agk/evidence.py push --branch <branch>`. `--record FILE`, hosted, hybrid and pool
   mode and personal mode write no note.
2. `scripts/agk/evidence.py push --branch <b> [--remote <r>]` (default `origin`) fetches the remote's notes ref into
   `refs/notes/agk-evidence-origin`, merges it into the local ref with the `ours` strategy (notes are keyed by head, so
   two machines never write the same one), then runs `git push <r> <b> refs/notes/agk-evidence`. When the branch
   reached the remote and only the notes ref was refused, it prints one line naming the setting
   `refs/notes/agk-evidence` and the fallback, the record copied by hand as before, and exits 0; any other failure
   keeps git's exit code.
3. `scripts/agk/evidence.py check --head <sha>` with no RECORD reads the shared folder first, so one machine makes no
   fetch. When the folder has no record it runs one `git fetch origin +refs/notes/agk-evidence:refs/notes/agk-evidence-origin`
   and reads the note of that head from the fetched ref, printing `evidence: record read from the note of the head
   (ref: refs/notes/agk-evidence)`. No note, no remote or a refused fetch is exit 3 with the line of today. The fetched
   ref is a separate one so that the clone's own notes are never overwritten.
4. A note is evidence to re-check, never a pass: it is loaded and checked exactly as a record file (`stale`, `dirty`,
   `failed`, governance in a clean worktree, the sampled re-run), and the printed `record <sha12>` is the digest of the
   note's bytes, which the conductor compares with the builder's `Evidence:` line as today.
5. `docs/guides/local-mode.md`: the cross-machine paragraph names the note and `evidence.py push`, and keeps the copy by
   hand as the fallback.

No workflow, ruleset, required check or `constitution/` file changes. Hosted and hybrid mode keep CI as the evidence.

## Consequences

A member's local-mode pull request is cleared from another machine with no file copied. The note is plain data in the
project's own remote, with no new service and no token. The notes ref is not part of any branch, so it never reaches the
default branch. Tests: `tests/kit/test_evidence_travels.py`. Protected path classes changed: `scripts/agk/` (`prepush.py`,
`evidence.py`) and `tests/kit/` (`test_evidence_travels.py`).

## Residual

- 2026-11-17: the fetch in rule 3 uses a separate ref (`refs/notes/agk-evidence-origin`) where the brief named the local
  ref itself, so that a conductor's own notes are never overwritten (Q-1447-1).
- 2026-11-17: notes of old heads stay on the remote until a person removes the ref; each is one small record.

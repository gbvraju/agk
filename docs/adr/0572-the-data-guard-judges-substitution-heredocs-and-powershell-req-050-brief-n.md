# ADR-0572: The data guard judges substitution, here-documents and PowerShell; prepush and the doctor say more

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: brief #1360, brief #1269, brief #1329, ADR-0536, ADR-0564, plan #661
- Requirements: REQ-050

## Context

Brief #1360 carries three findings from one builder's log in an adopted project in local mode on Windows: the data
guard (`.claude/hooks/data_guard.py`) refused compound shell lines, `scripts/agk/prepush.py --record` printed a
record id but not where the record went, and the first edit of a file rewrote its line endings. Each cost a retry.

## Decision

1. The data guard: pending Q-1360-1 (the measured cause differs from the brief's; see the pull request).
2. Prepush's `Evidence:` line ends `record <sha12> in the shared evidence folder` when `--record` has no FILE, and
   `record <sha12> in the given file` otherwise. With no FILE one more line follows,
   `prepush: read it with python3 scripts/agk/evidence.py check --head <sha12>`. No path and no user name is
   printed. The line still matches the router's `Evidence:` pattern.
3. On Windows, when `git config core.autocrlf` is `true` and the project's `.gitattributes` has no line whose pattern
   is `*` with an `eol=` attribute, `scripts/agk/doctor.py` prints
   `line endings: this machine rewrites LF to CRLF; add "* text=auto eol=lf" to .gitattributes (setting: core.autocrlf)`.
   The kit does not change the project's `.gitattributes`; `docs/guides/local-mode.md` names the line.

## Consequences

A builder learns where its record went and how to read it, and is told before the first edit that line endings
will be rewritten. Protected path classes changed: `scripts/agk/` (`prepush.py`, `doctor.py`) and `tests/kit/`
(`test_prepush_record.py`, `test_evidence_location.py`, `test_doctor_windows.py`).

## Residual

- 2026-11-15: only a `*` line with `eol=` silences the doctor's warning; a project that sets `eol` per extension
  still sees it, which is advice and fails nothing.

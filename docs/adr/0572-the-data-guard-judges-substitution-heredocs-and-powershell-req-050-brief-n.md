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

Measured on main at 945c05a (Q-1360-1): a line holding `$(`, a backquote, `<<`, `<(` or `>(` was not refused whole, as
the brief said; it was judged on its raw text, where every word, the data of a here-document included, went through the
path and glob checks. A `*` bullet of a commit message was expanded in the folder and met a log file (`raw-log`), and
the folder check of a recursive search after such a form was skipped. The maintainers ruled (a): build answer 1 as
written, with the measured "before" corrected.

## Decision

1. The data guard (`.claude/hooks/data_guard.py`) takes apart three forms that SPEC-0042 rule 4 judged on their raw
   text, and judges each part by the rules it already has. (a) A `$(...)`, `<(...)`, `>(...)` or backquote command is
   judged as a nested shell within the depth of 3, and the outer line with a placeholder word; a substitution that
   holds a decoder denies `decoded name`, and a word that joins the placeholder to other text is matched against the
   denied names with the placeholder as `*`. (b) A here-document's delimiter is read; its body is data, searched for a
   denied name and never expanded as a glob; with an unquoted delimiter its substitutions are judged as (a); the
   command before it is judged as usual. A here-string (`<<<`) stays a redirection. (c) A line of the PowerShell tool,
   of a `pwsh`/`powershell -Command` argument, or of a session whose `SHELL` names `pwsh` or `powershell`
   `(verify)`, reads the backquote as PowerShell's escape and line continuation, is split at `;`, `|`, `&&`, `||` and
   line ends, judges its `$(...)` as a nested PowerShell line and drops the call operators `&` and `.`.
   A form it cannot take apart (an unclosed substitution or here-document, a backquote holding a backslash) denies
   `cannot-judge (compound form)`; that line and `cannot-judge (nested shell)` add `split it into single commands, or`
   before the alternative. A line with a `#` outside quotes, or with unbalanced quotes, is judged on its raw text as
   before. The rules of what is denied do not change.
2. Prepush's `Evidence:` line ends `record <sha12> in the shared evidence folder` when `--record` has no FILE, and
   `record <sha12> in the given file` otherwise. With no FILE one more line follows,
   `prepush: read it with python3 scripts/agk/evidence.py check --head <sha12>`. No path and no user name is
   printed. The line still matches the router's `Evidence:` pattern.
3. On Windows, when `git config core.autocrlf` is `true` and the project's `.gitattributes` has no line whose pattern
   is `*` with an `eol=` attribute, `scripts/agk/doctor.py` prints
   `line endings: this machine rewrites LF to CRLF; add "* text=auto eol=lf" to .gitattributes (setting: core.autocrlf)`.
   The kit does not change the project's `.gitattributes`; `docs/guides/local-mode.md` names the line.

## Consequences

Ordinary multi-line commits and PowerShell lines pass part by part, and a recursive search after a substitution meets
the folder check. This supersedes, for the three forms, SPEC-0042 rule 4's sentence that a command it cannot split is
judged on its raw text and otherwise allowed; the spec's text is the reviewers' to patch. A builder learns where its
record went and how to read it, and is told before the first edit that line endings will be rewritten. Protected path classes changed: `.claude/` (`hooks/data_guard.py`), `scripts/agk/` (`prepush.py`,
`doctor.py`) and `tests/kit/` (`test_data_guard_forms.py`, `test_prepush_record.py`, `test_evidence_location.py`,
`test_doctor_windows.py`).

## Residual

- 2026-11-15: SPEC-0042 rule 4 still says a command it cannot split is judged on its raw text; the reviewers patch it.
- 2026-11-15: a value built at run time (`cat $(ls | grep env)`) is still not caught, as SPEC-0042 rule 16 says.
- 2026-11-15: whether Claude Code sets `SHELL` to `pwsh` in a PowerShell session is `(verify)`; the PowerShell tool
  and a `pwsh -Command` argument are read as PowerShell whatever it says.
- 2026-11-15: only a `*` line with `eol=` silences the doctor's warning; a project that sets `eol` per extension
  still sees it, which is advice and fails nothing.

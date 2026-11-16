# ADR-0593: Every hook refusal is kept on the machine, redacted, and a hook error names what failed

- Status: Accepted
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1410, brief #1360, ADR-0572, ADR-0268, plan #661
- Requirements: REQ-050

## Context

Brief #1410 reports what happened in a project adopted in local mode on Windows. The data guard refused commands it should
have been able to judge, a seed run against a throwaway database among them, and said only `cannot-judge (hook error)`.
The builder's refused command was then lost when its session closed. On main at 3fe470b, `judge()` in
`.claude/hooks/data_guard.py` turns any exception into that denial and keeps nothing, and no hook records what it
refused. Reproducing the project's seed runs on a Windows-shaped fixture (a PowerShell session, backslash paths, CRLF line
ends) found one case that failed: a here-document whose lines end in CRLF was refused as `compound form`, because the
delimiter line `SQL\r` never matched `SQL`. No hook error came up on Linux; the project's own error stays `(verify)`.

## Decision

1. Each of the four hooks (data guard, conductor guard, steward guard, architect guard) appends one JSON line per denial to
   `<git common dir>/agk/refusals.log`, through `scripts/agk/guard_logs.py`'s `record_refusal`. The common dir is found by
   reading `.git` and its `commondir` file, without running a program. Each line holds `at` (UTC, from the clock),
   `session` (`AGK_SESSION`, else the hook input's `session_id`), `role` (`AGK_ROLE`, else the hook's own role), `hook`,
   `reason` and `text`. `reason` is a code: the data guard's rule and kind, the name of the conductor's or architect's
   `*_RULE` text, or the steward's path class. `text` is the command or path after `guard.scan_text` redaction, cut at 500
   characters. The file is never tracked and never posted. It rolls over at 1 MB, keeping one older file
   (`refusals.log.1`). A write that fails returns, and the denial is unchanged. An allowed call writes nothing.
2. For `cannot-judge (hook error)` the line adds `error`, with the exception's type and the deepest function and line in the
   hook's own file. The exception's message is never kept. The denial message adds `; see agk logs --refusals`.
3. `agk logs --refusals` (`guard_logs.py --refusals`) prints the older file and then the current one through the same
   redaction, or `agk logs: no refusals recorded`. `agk status` prints `refusals today: <n> (<reason> <k>, ...)`, or
   `refusals today: none`. The data guard's raw-log rule still denies any other read of the file.
4. In the data guard, a here-document line with a CRLF line end closes the here-document as the same line without its
   carriage return does. The body stays data and is still searched for a denied name. The lines after the delimiter are
   judged as commands, which is never less strict than bash, whose body runs at least as far.

## Consequences

This changes SPEC-0042 rule 15 for this one file, which says a guard record never holds a path or a command: the refusal
log keeps the refused command or path, redacted, because that is the only way to find and fix a guard's mistake. The guard
log of rule 15 is unchanged. The spec's text is the reviewers' to patch. A denied command no longer ends with its session,
and an internal error says where it happened. Protected path classes changed: `.claude/` (`hooks/data_guard.py`,
`hooks/conductor_guard.py`, `hooks/steward_guard.py`, `hooks/architect_guard.py`), `scripts/agk/` (`guard_logs.py`,
`autopilot.py`) and `tests/kit/` (`test_refusal_log.py`).

## Residual

- 2026-11-16: the adopted project's own `hook error` was not reproduced on Linux `(verify)`. Its refusal log will name the
  type and place on the next occurrence, and the commands from its report, once the owner supplies them redacted, become
  tests.
- 2026-11-16: whether every Claude Code version passes `session_id` in the hook input is `(verify)`; without it and without
  `AGK_SESSION` the line says `unknown`.
- 2026-11-16: in CI mode the log belongs to the runner and ends with the run.
- 2026-11-16: part 2 of the brief (the kit-defect channel and the steward's reads) is not built here.

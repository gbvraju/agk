# ADR-0610: Kit entry points refuse in one plain line

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1452, ADR-0589
- Requirements: REQ-071

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

`autopilot.py next` run from a product clone in personal mode without `--root` naming the sidecar printed a Python
traceback ending `common.CheckError: rule 3: the open briefs cannot be read`: `autopilot.py` had no handler for the
kit's own refusal error, so a business user read a stack trace instead of what to do next. `session.py` and
`conductor.py` already turned the error into one `FAIL session:` or `FAIL conductor:` line, except the conductor's
`watchdog --install` line, which read the repository root outside its handler.

## Decision

1. The `main` of `autopilot.py` catches the refusal error (`CheckError`) and prints `refused: <message>` on standard
   error, exit 1. Any other exception keeps its traceback.
2. `session.py` and `conductor.py` keep their existing one refusal line and exit code (`FAIL session: <message>` on
   standard output, exit 2; `FAIL conductor: <message>` on standard error, exit 1), so no caller or test that reads
   them changes; the conductor's `watchdog --install` reads the root inside the same handler.
3. In all three, when the folder is a clone with no `agk.toml` with a version and a sidecar is registered for it
   under `AGK_HOME` (`common.root_hint`, which reads the registry first and runs no process when there is none, and
   imports the kit-only `personal_state` only when it is there), the line ends `(personal mode: pass --root <the sidecar's folder>)`,
   naming the option and never the path or the project id. A failure to read the clone or the registry adds nothing.

## Consequences

Every mode reads one line instead of a traceback, and the personal-mode case says how to fix itself. The wording of
the three lines stays different (Q-1452-2 asks whether to unify it on `refused:`).

## Residual

- Q-1452-2: one wording for all three entry points.

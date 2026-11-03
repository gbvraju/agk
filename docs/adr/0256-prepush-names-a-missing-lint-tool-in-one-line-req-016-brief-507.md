# ADR-0256: prepush names a missing lint tool in one line (REQ-016, brief 507)

- Status: Proposed
- Date: 2026-11-03
- Deciders: maintainers
- Related: ADR-0186, ADR-0208, ADR-0254
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

In the pilot (#479), on Windows without ruff on the PATH, `prepush.py` stopped at the lint step with
`process_begin: CreateProcess(NULL, ruff check ...) failed` and `make (e=2)`, and the session lost time reading the
error, while a missing gitleaks already reads `secret scan: not run` with a reason. Brief #507 asks for one line that
names the missing command. This ADR number was reserved for brief #507 by the conductor (the field note on #507).

## Decision

1. When `make lint` exits non-zero and its output shows that a command could not be started, the lint step is a FAIL
   with the one line `lint: the lint target runs <cmd>, which is not installed (target: lint); install it (for
   example: uv tool install <cmd> or pip install <cmd>) and run prepush again`, and the raw output is not echoed.
2. The signs are `CreateProcess(NULL, <cmd> ...) failed`, `<cmd>: command not found`, `<cmd>: not found`,
   `<cmd>: No such file or directory` together with an exit of 127 (make's own exit, or its `Error 127` line), and an
   exit of 127 alone, where `<cmd>` is the first word of the last command line make echoed. `<cmd>` is shown by its
   file name, without a folder or an `.exe` suffix. When no command can be named the output prints as before.
3. Any other lint failure prints as before; the record of ADR-0208 still holds the real exit and the digest of the
   real output.
4. The step stays a FAIL, never `not run`: lint is a rule of the project, unlike the optional secret scan. The rule
   is written in the module docstring of `prepush.py`.

## Consequences

A session without a lint tool reads one line that names the tool and the install command, on Windows and POSIX
alike, and the push stays blocked as before. Nothing is installed, and the governance step's own handling of a
missing make is unchanged.

## Residual

- 2026-11-03: a recipe that hides its command (`@`) and exits 127 without a shell message gives no command to name,
  so its output prints as before (Q-507-2).

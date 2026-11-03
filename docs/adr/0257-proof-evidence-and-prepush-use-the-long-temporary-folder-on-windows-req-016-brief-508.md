# ADR-0257: proof, evidence and prepush use the long temporary folder on Windows (REQ-016, brief 508)

- Status: Accepted
- Date: 2026-11-03
- Deciders: maintainers
- Related: ADR-0233, ADR-0253, ADR-0256
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

In the pilot (#493), `proof.py` reported `not proven` (frontend red on head) with `Cannot find module
/src/test/setup.ts` because `TEMP` and `TMP` held the Windows 8.3 short form of the temporary folder (a
folder name such as `EXAMPL~1.USR`). With the long form the same head was proven. `proof.py` and
`evidence.py` call `tempfile.mkdtemp` with the default folder, and `prepush.py` hands the environment to
the test commands unchanged. This ADR number was reserved for brief #508 by the conductor (the field
note on #508).

## Decision

1. `scripts/agk/common.py` gains `long_temp_dir() -> Path`. On Windows (`os.name == "nt"`) it is
   `tempfile.gettempdir()` expanded with `GetLongPathNameW` through `ctypes`, or the value unchanged when
   the call fails or cannot be made. Elsewhere it is `Path(tempfile.gettempdir())`. The text it wraps is
   `long_temp_name()`, and `temp_env(base)` returns a copy of an environment (the process environment by
   default) with `TEMP`, `TMP` and `TMPDIR` set to it on Windows, and an unchanged copy elsewhere.
2. `proof.py` and `evidence.py` make their temporary folders with `mkdtemp(dir=long_temp_dir())`.
3. `proof.py` runs each test command of its runs on the base and the head and of its regression run,
   `prepush.py` runs each test command of its tests step (with or without a `[testing]` table), and
   `evidence.py` runs governance and every re-run unit, with the environment of `temp_env`. `execute` in
   `proof.py` takes an optional environment; without one it inherits as before, so the drift audit and
   every other caller are unchanged.
4. Nothing changes on POSIX: the folder is `tempfile.gettempdir()` and the environment is the caller's.

## Consequences

On Windows a front-end suite that resolves its setup file from the temporary folder sees the same long
path in all three variables, whatever form the session's own `TEMP` holds. A failed expansion leaves the
value as it was, so a run never fails for this reason alone. `prepush.py`'s governance and lint steps
and the drift audit keep the caller's environment.

## Residual

- 2026-11-03: the launch adapter's own environment (brief #506) and any other path shortening are out
  of scope; a project command started outside these three scripts still sees the session's `TEMP`.

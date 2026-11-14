# ADR-0524: Every installed check writes UTF-8

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0160, ADR-0200, ADR-0522, brief #263, brief #1223, brief #1233, plan #661
- Requirements: REQ-014

## Context

On a customer project on Windows 11 (kit 0.64.1), `make -f agk.mk agk-governance` stopped with
`UnicodeEncodeError: 'charmap' codec can't encode character '→'`: `check_plan.py` printed a design heading with an
arrow, and Python writes a Windows console in its code page (cp1252). With `PYTHONUTF8=1` every check passed, so every
Windows user needed `setx PYTHONUTF8 1`. Brief #263 (ADR-0200) made the kit read files and `git show` as UTF-8; nothing
made it write UTF-8. The same failure reproduces on Linux with `PYTHONIOENCODING=cp1252` and `PYTHONUTF8=0`.

## Decision

1. `scripts/agk/common.py` gains one helper, `utf8_output()`, that reconfigures `sys.stdout` and `sys.stderr` to UTF-8
   with `errors="replace"` when the stream has `reconfigure` (a text stream) and is not already UTF-8. A stream that is
   already UTF-8, or that has no `reconfigure`, is left as it is, so a caller that captures output keeps its stream.
2. Every installed script under `scripts/agk/` that prints and runs as a program (`kit/manifest.json`, `verbatim` or
   `experimental`) calls it as the first statement of its `main`, after the docstring. `common.py` and
   `session_plan.py` are libraries that print only under their caller's `main` and do not call it. The scripts that
   did not import `common` (`guard_logs.py`, `lessons.py`, `parity.py`, `pr_state.py`, `usage.py`) import the
   helper alone, after the line that puts their folder on `sys.path`. Three scripts must run without `common`:
   `product_report.py` imports no module of the kit (its rule 13: `common` imports `os` and `subprocess`),
   `new_spec.py` only the standard library, and `front_door.py` imports `common` only inside the functions that need
   it, so its tests run it copied alone. Each keeps its own copy of the helper, which a test keeps equal to
   `common`'s. Nothing else they print changes.
3. `tests/kit/test_output_encoding.py` proves it: the helper under the simulated console; `check_plan.py` and
   `config.py` printing an arrow exit and print as on a UTF-8 console; every such script, given an option it refuses,
   exits as on a UTF-8 console and lets an arrow written after its start reach the console; and every such script calls
   the helper first, and that each of the three copies is the helper.

## Consequences

Governance and every other installed check run on a Windows console without `PYTHONUTF8`. A console that cannot show a
character shows what the console makes of UTF-8 bytes; the check no longer stops. Output to a pipe or file is UTF-8 on
every platform, as CI's Linux runners already wrote it. The hooks under `.claude/hooks/` are outside this decision (the
brief's `Touches:` names `scripts/agk/` only). No workflow changes.
Protected path classes changed: `scripts/agk/` (`common.py` and the 73 installed scripts that print), `tests/kit/`
(`test_output_encoding.py`, new) and `docs/adr/` (this file).

## Residual

- 2026-11-14: the fix is proved with a simulated cp1252 console on Linux; it was not run on a Windows console by the
  session that wrote this `(verify)`.

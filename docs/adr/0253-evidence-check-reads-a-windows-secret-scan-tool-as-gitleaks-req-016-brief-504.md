# ADR-0253: evidence check reads a Windows record's secret-scan tool as gitleaks (REQ-016, brief 504)

- Status: Accepted
- Date: 2026-11-03
- Deciders: maintainers
- Related: ADR-0233, ADR-0208
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

In the pilot (AGK 0.63.0 on Windows, #495), every pull request with a real secret scan read
`evidence: not what prepush runs: secret-scan (field: argv)` and `Evidence check: differs`. On Windows, prepush records
the scan's tool as `shutil.which` gives it, a path that ends in `gitleaks.EXE`, while `scripts/agk/evidence.py` compared
`Path(recorded[0]).name` with `gitleaks` exactly. The owner had to accept `differs` by hand on every merge. The
conductor reserved this ADR number for brief #504.

## Decision

1. `scripts/agk/evidence.py` has a function `tool_name(argv0)` that returns the executable's base name, lower-cased,
   with one trailing `.exe` removed. A value that holds a backslash is read as a Windows path (`PureWindowsPath`), on
   any operating system; any other value is read as a POSIX path.
2. The secret-scan comparison uses `tool_name(recorded[0]) != "gitleaks"`. Every other check of that step is unchanged:
   the tail must match exactly, and the step is `not repeatable` when gitleaks is not installed here.
3. Nothing else is loosened. Another tool name (`gitleaks2.exe`, `leaks`, `leaks.exe`, `gitleaks.exe.exe`) still reads
   `differs` on argv, and no other step's comparison changes.
4. The tests are `tests/kit/test_evidence_windows_tool.py`, with invented records under `tmp_path`, run on a POSIX
   runner.

## Consequences

A Windows record of a real secret scan agrees when the scan repeats with the same exit, so the owner no longer accepts
`differs` by hand. How prepush records the tool is unchanged.

## Residual

- 2026-11-03: none.

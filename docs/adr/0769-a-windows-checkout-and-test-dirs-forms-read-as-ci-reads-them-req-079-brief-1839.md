# ADR-0769: The Node format step keeps each file's line end, and every reader reads `test_dirs` as one folder (REQ-079)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers
- Related: SPEC-0072 rule 6, ADR-0160, ADR-0490, ADR-0648, ADR-0669, ADR-0680, ADR-0730, ADR-0739, brief #1360, brief #1839, plan #661
- Requirements: REQ-079, REQ-062

Protected classes this pull request changes: `scripts/agk/` (`common.py`, `gates/node_pack.py`) and `tests/kit/`
(`test_node_pack.py`, `test_impact.py`, `test_test_plan.py`, `test_agk_config.py`, `test_gate_injection_set.py`, the new
`test_windows_forms.py`).
`kit/hashes.json` is not edited by hand.

## Context

On main at 9f34c84 (2026-11-23) a Windows machine and CI give different results for the same commit. Git for Windows
(`core.autocrlf = true`) checks a project's files out as CRLF, while every checkout the kit makes, and the hosted job,
reads LF (ADR-0648). The Node pack's `node-format` step ran `prettier --check` with prettier's default `endOfLine: "lf"`,
so every CRLF file failed locally and in an adopted baseline, while the Python pack's `ruff format --check` keeps each
file's own line end (`line-ending = "auto"`). Separately, `test_dirs` reached most readers as written: `tests\`, `.\tests`
and `./tests` held no test file for `impact.in_test_dirs` (a full regression run), found no REQ marker through
`common._marker_files` on Linux, and were read as `tests` by `tests_floor` and `environment_settings` alone (ADR-0730).

## Decision

1. `node_pack.format_check` runs `prettier --check --end-of-line auto --config-precedence file-override <files>`
   (`node_pack.FORMAT_FLAGS`). With no line end set by the project, each file keeps its own, as `ruff format` does; a
   project's prettier configuration or `.editorconfig` that sets a line end wins, so an `lf` choice still fails a CRLF
   file, as `[tool.ruff.format] line-ending = "lf"` does in the Python pack. The kit's default for line ends follows ruff
   and git (`core.autocrlf` changes only the working copy), not prettier's default. This does not weaken the step
   (principle 11): every content fault fails as before, and its lines, tally and exit codes are unchanged. The kit still
   never writes the project's `.gitattributes` (brief #1360); `doctor.py` keeps advising `* text=auto eol=lf`
   (`Q-1839-1`, the brief's `Q-HG-1`: the conservative reading; the owner may choose an LF-only floor for both packs).
2. `common.load_config` reads each string entry of a `test_dirs` list as one folder (`common.test_folder`): a back slash
   is read as `/`, leading `./` parts and a trailing `/` are dropped, and `.` or an empty entry is `.`, the repository
   root. `common.test_dirs` reads a `--dirs` value the same way. A non-string entry, or a `test_dirs` that is not a
   list, is returned as written, so `environment_settings` still refuses it naming `test_dirs`. Every reader that goes
   through `load_config` (`impact`, the marker readers of `common`, `check_requirements.py`, `check_plan.py`,
   `check_kit_tests.py`, `drift_audit.py`, `facts.py`, `proof.py`, `doctor.py`, `tests_floor`, `environment_settings`,
   `injection_set`) therefore sees `tests` for each written form, on Linux and on Windows. A Linux folder whose name holds
   a back slash cannot be named (`Q-1839-2`, the brief's `Q-HG-2`); `[testing]` map globs keep refusing `\`. The
   `injection-set` step, which refused a back-slash entry (brief #1712), now reads it as its folder, as the tests floor
   does; it still refuses a non-list, an empty, a non-string and a `..` entry (`Q-1839-4`).
3. `tests/kit/test_windows_forms.py` keeps the class closed: each pack gives an LF file and its CRLF twin the same format
   result, every reader above reads one folder for each form, and a scan of `scripts/agk/` fails a file that reads
   `test_dirs` from the raw settings (`config_source(...)` or a TOML read) past `load_config`, naming the file.

## Consequences

A Windows person's `make governance`, `prepush.py`, the clean project's governance command and an adopted baseline give
the result CI gives for line ends; an existing Node format baseline that counted CRLF files falls (`a count fell`,
lowered by `run_gates.py --baseline`), never a failure. A back-slash or `./` `test_dirs` keeps a mapped one-file selection
instead of a full run, and the REQ markers CI finds are the ones the person's machine finds. Other path lists of
`DEFAULT_CONFIG` (`lint_paths` and the rest) are still read as written (`Q-1839-3`, the brief's `Q-HG-3`).

## Residual

- 2026-11-23: the stamped `test_dirs` that `adopt.py` reads back from its own stamp file is not normalised here; the kit
  writes that stamp itself, so it holds the forward-slash form (verify on a Windows adopt run).

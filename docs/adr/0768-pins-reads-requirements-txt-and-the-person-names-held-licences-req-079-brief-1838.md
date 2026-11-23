# ADR-0768: The pins step reads a Python project's requirements files, and the person can name each failing licence (REQ-079)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers
- Related: SPEC-0072 rules 4 and 7, SPEC-0054 rule 4 (amendment 206), ADR-0672, ADR-0676, ADR-0680, ADR-0742, ADR-0743, ADR-0744, brief #1838, plan #661
- Requirements: REQ-079, REQ-061

Protected classes this pull request changes: `scripts/agk/` (`gates/pins.py`, `gates/licences.py`, `doctor.py`) and
`tests/kit/` (`test_pins_requirements.py`, `test_product_deps.py`, `test_doctor_project_lines.py`). `kit/hashes.json`
is not edited by hand.

## Context

On main at e1fdb41 (2026-11-23) the `pins` step of a Python stack reads only `[project] dependencies` and
`optional-dependencies` of `pyproject.toml`. An existing Python service that declares its dependencies in
`requirements.txt`, or names that file from `[tool.setuptools.dynamic]`, passes `ok pins` with ranges and bare names
in it (run record 7100000199, AD-06). An adopted project's held licence findings are counted by class only (ADR-0743),
so the person learns that a package fails and never which.

## Decision

1. With the chosen runtime `python`, `pins.python_files(root)` is the one list of the Python dependency files: the
   build file `pyproject.toml`, the root `requirements.txt` when present, each file of `[tool.setuptools.dynamic]`
   `dependencies` and `optional-dependencies`, and each file a `-r` or `--requirement` line of a read file names,
   relative to that file, each read once. A file outside the root, an absolute path or a missing file is the
   `the build file is missing or unreadable` line, held to the including file. A `-c` file, index and install options,
   comments, blank lines, continuations and per-requirement options (`--hash=`) are not dependencies. Any other line
   is a requirement: `name==1.2.3` is pinned; a range, a bare name, a wildcard, a URL or `@` reference, an `-e` line
   other than `-e .` and a line of no requirement form are `not pinned exactly`. Each finding is held to the file it is
   in; a name declared in several files is one finding, held to the first file where it floats. The lines keep their
   form: the rule and the component class, never a name or a version. `requirements.lock` stays the lock.
2. `gates/licences.py --names` prints, on the person's machine, one line per lock package whose licence is off the
   allowed list or unknown, `licence off the list: <class> <package> <licence id or unknown> (path class: <lock>)`,
   sorted, then `licences: <n> to name; the baseline holds <m> (path class: config/agk-baseline/)`, or
   `ok licences (none to name)`; exit 1 when it lists one, else 0, writing nothing. No workflow, gate run or
   `prepush.py` step calls it.
3. Principle 8 is read so: a refusal and a gate row name the setting or path class, never a value, and stay as
   ADR-0676 and ADR-0743 wrote them; a package name and licence id of a committed lock are printed only by a command
   the person runs to decide them (`Q-1838-1`, the brief's `Q-HF-1`).
4. `doctor.py` prints one `warn licences:` line while `config/agk-baseline/licences.txt` holds a line, naming the count
   of held packages and the `--names` command with `<kit>` from `kit_root.form`; it changes no exit code. Another
   `[kit] layout` is refused naming `layout`.

## Consequences

An adopted Python service whose `requirements.txt` floats learns it on its first gate run, where its baseline holds
the findings per file; one whose `pins.txt` was written before this build fails `SPEC-0072 rule 7` on its next run
until it pins them (principle 11). A Node stack is unchanged. The person names a held licence with one command, and CI
logs and refusals print no name.

## Residual

- 2026-11-23: `requirements-dev.txt`, `requirements/*.txt` and `requirements.in` that nothing names are not read
  (`Q-1838-2`); the licence baseline still counts per lock, so a held package swapped for another off-list one is held
  (`Q-1838-4`), and `--names` shows the new one.

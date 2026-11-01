# ADR-0240: the weekly drift audit runs a project's optional mutation-testing command on recently changed code (REQ-011, brief 449)

- Status: Accepted
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0177
- Requirements: REQ-011

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`

## Context

The drift audit already runs a project's optional `unused_code` and `coverage` commands and lists them as D9 (SPEC-0004
rule 25, amendment 87, ADR-0177). Coverage says which lines ran, not whether the tests would notice a wrong line. Mutation
testing measures that: a tool injects small faults and counts how many the tests catch. Brief #449 (#289 part 5) puts it in
the same slot, as a measurement that is listed and never blocks. The kit ships, installs and chooses no tool.

## Decision

1. **The setting (answer 1).** `agk.toml` gains `mutation`, a shell command like `coverage`, empty (off) by default.
   `common.py` names it in the defaults next to `coverage`; both templates name it empty with one comment line. This
   repository's own `agk.toml` is not changed (the default fills it; Q-449-2).
2. **The changed code files (answer 1).** The report run lists the code files changed on the default branch in the last 7
   days: the paths added or modified by the first-parent commits of the audit's window (the window of D1), that still exist
   on the default branch, that are not documentation (a `.md` file or a path under `docs/`) and not a test file
   (`test_dirs` and `test_patterns`), the same reading of "code" that `impact.py` uses for an unmapped file (Q-449-1). The
   list is sorted by name and cut at 20, so a run can be repeated. It is written one path per line to a file in a temporary
   directory outside the checkout, which is removed after the run; `AGK_CHANGED_FILES` names that file. The command runs
   through `proof.execute` within `proof_timeout`, standard output only, as the other two; `AGK_CHANGED_FILES` is exported
   by a line the audit puts before the command, so `proof.py` does not change (Q-449-3).
3. **The line (answer 2).** The score is the percentage on the last line of a command that exits 0 (0 to 100, `%`
   allowed), read as coverage is read. The finding is `D9 mutation`, with the sentence
   `killed <n>% of injected faults in <k> files, change since the previous audit: <change>` (`1 file` in the singular).
   The change is read from the `D9 mutation` line of the previous audit (`--previous FILE`), as for coverage, and is
   `unknown` when there is none. A command that fails, runs too long or prints no readable number reads `unknown`, never
   a number; the line is listed and never blocks.
4. **No changed code file (answer 3).** The command is not run, and the sentence is
   `not run: no code file changed on the default branch in the last 7 days`.
5. **Where it runs.** Only the report run starts the command; `--print-action` counts a set `mutation` like the other two,
   so the issue is written without running it. The report never shows the command.
6. **The guide (answer 4).** `docs/guides/testing.md` gains a section naming the setting, `AGK_CHANGED_FILES` and the line,
   with one invented example command.
7. **Tests first (answer 5).** `tests/kit/test_drift_mutation.py` uses fake shell commands: a score, no number, a failing
   command, no changed file, the setting unset, and the list itself. `tests/kit/test_agk_config.py` gains the default.
8. **The spec (answer 6).** `docs/runs/proposed-spec-amendments-106.md` proposes, in the form of amendment 105, the mutation
   line under SPEC-0004 rule 25. It is a proposal only; no rule of the spec changes.

## Consequences

A project that sets `mutation` sees each week what share of injected faults its tests caught in the code changed that
week, and how it moved. A project that does not set it sees nothing new. Nothing blocks on a low score.

## Residual

- 2026-11-01: Q-449-1: "code files" is not defined by the brief. Read as impact.py reads an unmapped file: not
  documentation and not a test file, so a changed configuration file is listed too; the project's command may skip what its
  tool cannot mutate.
- 2026-11-01: Q-449-2: the brief's `Touches` does not name this repository's `agk.toml`; the default (empty) applies, so it
  is left unchanged.
- 2026-11-01: Q-449-3: `proof.execute` takes no environment; rather than change `proof.py`, which the brief does not name,
  the audit exports `AGK_CHANGED_FILES` in a line before the project's command.

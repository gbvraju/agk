# ADR-0359: A file the test map does not cover selects the tests that name it (REQ-051, REQ-062, brief 773)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: SPEC-0055, ADR-0360, ADR-0220, ADR-0285, ADR-0348, plan #661
- Requirements: REQ-051, REQ-062

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `agk.toml`

## Context

SPEC-0055 rule 6, build (b), brief #773. Under the `balanced` profile a changed file that no `[[testing.map]]` entry
covers makes a pull request's selection full, so a change of a data file (`kit/manifest.json`, `config/playbooks/*.toml`)
ran the full suite on the pull request and again on the default branch after its merge. Reproduced on governance run
42475854430 of 2026-11-08: `regression: full (profile balanced: 2 unmapped files)`, naming
`config/playbooks/default.toml` and `kit/manifest.json`. ADR-0360 leaves this build its own ADR.

## Decision

1. Under `balanced`, for a changed file no entry covers, `impact.py` selects the test files of the head that name its
   path or its folder, and the selection is full only when no test names it. It prints
   `unmapped: <path> -> <k> tests that name it`. There is no setting (SPEC-0055 rule 2). `fast`, `thorough`,
   `always_full`, a documentation-only change and a covered file whose entry selects no existing test are as before.
2. A name is a whole path-like word of the test file's text, read at the head. A top-level folder is named only by a
   word with its slash (`kit/`, `kit/a.json`), never by the bare word, which is ordinary prose.
3. `agk.toml` gains entries for the data files of brief answer 1, built from the code: each test file that names the
   path.
4. `check_kit_tests.py` fails a pull request that adds a file under `config/`, `kit/`, `skills/` or `.claude/` that no
   entry covers and no test names, naming the file and the rule. Here a test must name the file itself; the folder
   counts for the selection only.
5. `metrics.py` reads the mode line of each pull request run's job log and reports the share in `selected` mode, the
   minutes of the test step, the reason of each full run and the paths that most often made a run full. `doctor.py`
   lists the tracked files no entry covers and no test names.

## Consequences

A data-file change runs the tests that name it on the pull request; the default branch and a release still run
everything, so what this misses fails there and is a selection miss (SPEC-0055 rule 11). No workflow file changes.

## Residual

A test that reads a file through a path built at run time names only what its text holds; such a file falls to its
folder, or to a full run when nothing names it. The weekly lines show which paths still make a run full.

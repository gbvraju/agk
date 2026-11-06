# ADR-0299: Each pre-push test run writes to its own dated folder (REQ-051, brief 613)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0270, ADR-0208, ADR-0227, SPEC-0044, SPEC-0010
- Requirements: REQ-051

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

Pilot feedback #606 item 5: a rerun replaced the screenshots and trace of a real failure, because both runs wrote to the same
results folder. Brief #613 asks that every prepush and proof test run write to its own dated folder and that failure evidence be
kept. ADR-0270 names `scripts/agk/` and `tests/kit/` but not these new settings, their defaults or the retention rule, and not
`agk.toml`, so this build writes its own short ADR (brief #613 answer 6) instead of `Covered-by: ADR-0270`.

## Decision

1. `[testing]` gains three optional keys: `results_dir` (a folder inside the repository and below its root, with no
   default), `keep_passed` (false) and `keep_runs` (a whole number above 0, 20). A malformed value is refused naming the
   setting. The run folders are used only when `results_dir` is set (the conductor's answer to `Q-613-2`): SPEC-0044 rule 1,
   read strictly, says that with no new key prepush does exactly what the default branch does today, so without the key it
   sets no variable and makes no folder. This needs no amendment.
2. `proof.run_folder` makes `<results root>/<UTC time>-<head sha12>-<kind>` (a `-<n>` suffix if that name exists), sets
   `AGK_RUN_DIR` to it while the runs go and restores it after. The results root gets a `.gitignore` of `*` when it has none, so
   it is git-ignored in any project and a later record's `tree_clean` is unchanged. The kit adds no flag to the command.
3. After the runs a failed run's folder is marked and kept; a passed one is removed unless `keep_passed`. Then at most
   `keep_runs` run folders stay, oldest first removed, never a folder without a `passed` mark (failed, or still running) from the
   last 7 days. Only folders named as in 2 are ever removed.
4. With `results_dir` set, `prepush.py`'s tests step uses it with the kind `prepush` whenever it runs a command, and the
   `--record` file names it in a top-level `run_dir` object (`path` relative to the repository, `kept`); `evidence.py` already accepts an extra top-level field.
5. Proof's own runs do not use it in this decision: SPEC-0010 rules 8 and 11 (Approved) say proof changes nothing in ROOT's work
   tree and runs the command with no extra variables. The conductor's answer to `Q-613-1` keeps `proof.py`'s runs as they are
   here; that part needs an amendment of SPEC-0010, which the conductor files as its own brief. `proof.run_folder` is ready for
   it.
6. `agk.toml`'s `[[testing.map]]` entry for `scripts/agk/prepush.py` lists the new test file, so that a change of prepush
   selects it.

## Consequences

With `results_dir` set, a failed pre-push run's screenshots, traces and logs survive a rerun, and the record points at them.
With no new key nothing changes: prepush's argv, output, environment and work tree are as on the default branch.

## Residual

- 2026-11-06: proof's runs set no run folder until the SPEC-0010 amendment of the conductor's own brief (`Q-613-1`) is built
  (due 2026-11-20).

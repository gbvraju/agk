# ADR-0549: The guarded merge passes a clean environment without env

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0191, ADR-0254, ADR-0273, ADR-0297, ADR-0320, SPEC-0039, brief #551, brief #610, brief #667, brief #1264, brief #1290, plan #661
- Requirements: REQ-039

## Context

`merge_cleared.py` runs governance on the would-be merge before it merges and on the merge commit after it (SPEC-0039
rule 6, brief #610), and the pre-merge tests (brief #667), each as `lock.py run --name heavy ... -- env -i PATH=<PATH>
HOME=<scratch> ... make ...`. In a project on Windows (Git for Windows, local mode) the `env` found on PATH is the MSYS
`env`, which reads PATH as colon-separated POSIX folders while Python's PATH is Windows-form (`C:\...;C:\...`), so it
printed `env: 'make': No such file or directory` and every cleared pull request was held. The conductor's own runs go
through bash, whose PATH is already POSIX-form, so they worked.

Brief #1290 answers 1 and 2 ask for the clean environment to be passed to `subprocess` itself and for `lock.py run` to
pass the environment it is given to its command. Two facts of `lock.py` stand in the way of the literal reading: it
finds its lock folder from its own environment (the temp folder from `TMPDIR`, `TEMP` or `TMP`, and `lock_dir` with
`~` from `HOME`), so a lock.py started with the clean environment would take a different heavy lock than every other
run on a machine whose temp folder comes from `TMPDIR` (macOS); and it adds `AGK_LOCK_SESSION`, `AGK_LOCK_TOKEN` and
`AGK_LOCK_NAME` to its command's environment (ADR-0254), names `env -i` kept from the merged code.

## Decision

1. `scripts/agk/lock.py`: `run` takes `--only-env NAME=VALUE`, once per variable (NAME matching
   `[A-Za-z_][A-Za-z0-9_]*`, VALUE any text, `=` included; anything else is a usage error, exit 2). With at least one,
   the command is started with exactly those variables: none of lock.py's own environment and none of the `AGK_LOCK_`
   names. lock.py keeps its own environment for itself, so its lock folder, slots and queue are unchanged. Without the
   option nothing changes.
2. `scripts/agk/merge_cleared.py`: `governance_argv` and `tests_argv` no longer start `env`. They hand lock.py the run's
   clean environment with `--only-env`: exactly the names `env -i` kept (`PATH`, `HOME`, `AGK_PR_BODY` and
   `AGK_RECORD_COMMENTS` for governance; `PATH`, `HOME`, `AGK_KIT_TESTS=1` and `PYTHONDONTWRITEBYTECODE=1` for the tests),
   `PATH` taken unchanged from this process, so in its own separator, and on Windows only (`os.name == "nt"`, read
   through one function `on_windows` that tests fake) also `SystemRoot`, `ComSpec`, `PATHEXT`, `TEMP` and `TMP` where
   set. Nothing else of the process's environment reaches the merged code, as before. lock.py itself is started with
   this process's environment, as before.

No workflow file, ruleset or `constitution/` file changes.

## Consequences

On Windows the guarded merge starts `make` (or pytest) and a cleared pull request merges as on Linux. In CI mode (the
merger job on Linux runners) and locally on Linux or macOS the command gets the same variables as under `env -i`, and
the heavy lock is the same one. In personal mode there are no pull requests and nothing changes. The values travel in
lock.py's argument list as they did in `env`'s, and none is a secret. Tests: `tests/kit/test_merge_cleared_after.py`
and `tests/kit/test_merge_cleared_before.py` (a) no `env` or `-i` in either argument list; (b) exactly the kept names
on Linux; (c) with Windows faked and a `;`-separated PATH, that PATH unchanged and the five names added; (d) the real
lock.py starts a fake `make` found on a temporary PATH, exit 0 green and exit 2 `make governance`; the `--only-env`
option of lock.py, its refusals and its absence; (e) the existing tests, with their argument-list assertions moved from
`env -i` to `--only-env` (also in `tests/kit/test_merge_cleared_pre_tests.py`). Protected path classes changed:
`scripts/agk/` (`scripts/agk/lock.py`, `scripts/agk/merge_cleared.py`) and `tests/kit/` (the three test files above).

## Residual

- 2026-11-14: whether a Windows `make` found through the process's PATH by `CreateProcess` behaves as on Linux in a
  real customer project is not tested here (no Windows runner); the fix rests on the clean environment alone (verify).

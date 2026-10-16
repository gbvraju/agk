# ADR-0026: red-then-green, the proof check (SPEC-0010 (b)), kit 0.14.0

- Status: Proposed
- Date: 2026-10-16
- Deciders: maintainers
- Related: ADR-0021, ADR-0023, ADR-0024
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `.github/`, `tests/kit/`, `kit/`, `.claude-plugin/`

## Context

SPEC-0010 (Approved) part (b): can the tests a pull request adds fail? ADR-0024 landed part (a). This is the second pull request of
the day-12 split and serves exit criterion c of ADR-0021. Decisions of the maintainers that apply: Q-K4-25 (a `git worktree` of the base
and of the head, never `git archive`), Q-K4-30 (the jobs API is proved before the facts rely on it), Q-K4-37 (the pilot's seeded pull
request is opened by the pilot's own session).

## Decision

1. **`scripts/agk/proof.py`** (installed) implements rules 7 to 15. It adds two detached worktrees in a temporary directory outside the
   work tree, places the pull request's test files (path under `test_dirs`, name matching `test_patterns`) on the base, runs
   `project_tests` there (expected red) and on the head (expected green), and removes both worktrees, also on a failure. The outcome is
   `proven`, `not-proven` (`green-on-base`, `red-on-head`), `skipped` or `unknown` (`no-project-tests`, `no-test-files`, `timeout`) in the
   order of rule 12; exit 0, 1, 4; 2 usage; 3 I/O. Nothing in it names a language.
2. **`proof_timeout`** (seconds, default 900, a positive integer; anything else is a refusal that names the setting) is added to
   `common.DEFAULT_CONFIG` and to both `agk.toml` templates.
3. **`.github/workflows/proof.yml`** (installed): a job `proof` on `pull_request` (`opened`, `synchronize`, `reopened`, `edited`),
   `contents: read`, `fetch-depth: 0`, no secret, SHA-pinned actions, not a required check. One step runs `proof.py --head <pull request
   head> --body - --json` and fails only when `proof.py` itself failed; four steps `outcome: proven | not-proven | skipped | unknown`
   are guarded by its output, so exactly one succeeds and three are skipped. The ruleset is not touched.
4. **`Behaviour: unchanged`** (rule 18): `check_pr_body.py` accepts the exact line and fails any other `Behaviour:` line
   (`FAIL pr-body: 'Behaviour:' must be 'unchanged'`); the pull request template gains the optional line; one function in
   `common.py` (`declares_unchanged`) is used by the check, by `proof.py` and by `facts.py`. The declaration is counted, not judged.
5. **The jobs API is proved** (Q-K4-30): `docs/runs/proof-jobs-api.md` records that a completed job returns every step with its name and
   conclusion, skipped included. The reader of rule 17 in `facts.py` was built and tested against recorded run and job files in the
   facts ADR; it is unchanged.
6. **Tests** (installed): `tests/kit/test_proof.py` (21 cases built in `tmp_path` with a fake plain-shell `project_tests`: seeded,
   real change, declaration, no `project_tests`, no test file, deleted and renamed tests, red head, timeout, build failure on the base,
   a test-looking file outside `test_dirs`, a dirty work tree, clean-up, output, environment, JSON, usage), `tests/kit/test_pr_body_behaviour.py`,
   and additions to `tests/kit/test_workflow.py` (job name, events, permissions, no `pull_request_target`, pins, the four outcome
   steps, and the step's shell run in a throwaway repository).
7. **Live proof of the sandbox** (criterion b, rule 21 (c)) is recorded in `docs/runs/proof-checks-live-1.md`: the sandbox passes.
8. **Kit 0.14.0** (a minor: a new installed script, workflow and tests); the plugin version follows; `kit/hashes.json` is regenerated.

## Consequences

- Installed repositories receive the workflow and the script at their next `agk upgrade`; the job reports only, and blocks nothing.
- The first real `proof` job on `main` is read after this merges (`docs/runs/proof-checks-live-2.md`, a docs pull request of its own),
  together with the seeded pull request of rule 20.
- This repository's own `project_tests` runs no kit test (see `Q-K4-133`), so until that is decided a pull request that only adds kit
  tests reads `not-proven (green-on-base)` here.

## Questions

| Q | Question | Reading taken |
| --- | --- | --- |
| Q-K4-126 | Exit status of a refused setting and of an environment error. | an invalid `proof_timeout` is exit 2 (a refusal, with usage); an unresolved ref, no base, a directory that is not a work tree, or a worktree that cannot be added or removed is exit 3 |
| Q-K4-127 | Where the shown output goes when stdout is one line or one JSON object. | stderr, the last 40 lines of each run |
| Q-K4-128 | Rule 12 puts `timeout` before `proven` and `green-on-base`. | both runs are made unless run 1 times out, so that a timeout in run 2 wins over `green-on-base` |
| Q-K4-129 | An unedited template line `Behaviour: unchanged (optional; ...)` is not the exact line. | it fails the check, so the author deletes it or edits it to the exact line; indented lines and lines in a code fence are neither checked nor a declaration |
| Q-K4-130 | How the command is run and how tests are placed. | `sh -c COMMAND` in its own process group (the scanner-hygiene rule forbids `shell=True`), killed as a group on a timeout; a test file is read from the head commit with `git show` and written over the same path on the base worktree |
| Q-K4-131 | In a `pull_request` run `HEAD` is the merge commit. | the workflow passes `--head` the pull request's head SHA, which is also the `head_sha` that `facts.py` reads; the base is the merge base of `AGK_BASE` (the pull request base) and that head |
| Q-K4-132 | A `Behaviour:` declaration with no test change. | `skipped` is decided before `no-test-files`, as rule 12 orders |
| Q-K4-133 | This repository's `project_tests` is `python3 -m pytest tests -q --ignore=tests/kit_dev; ...`, and the kit tests are collected only with `AGK_KIT_TESTS=1` (as `agk-test` sets). The command collects nothing, exits 0 and so reads `green-on-base` on every pull request here (confirmed by running `proof.py --base origin/main` on this branch: `proof: not-proven (green-on-base)`). | nothing changed: the maintainers choose (point `project_tests` at the kit tests and drop the duplicate `agk-project-test` run, or keep the reading as a known false flag for rule 22) |
| Q-K4-134 | The sandbox (kit 0.9.0, `init` mode) counts 239 stray markers from the kit's own tests under `tests/kit/`. | nothing changed in the sandbox; strays never block; the maintainers decide whether its audit should exclude `tests/kit` as `adopt` mode does |

## Residual

- 2026-10-16: the `proof` job's step names are read from the first real run after this merges; if GitHub does not return them for that
  run, the fallback is the job summary, which is not machine-read (due 2026-11-16).
- 2026-10-16: a base that is red only because the pull request adds a dependency or a helper outside `test_patterns` is counted as proof
  (SPEC-0010 residuals; due 2026-12-31).

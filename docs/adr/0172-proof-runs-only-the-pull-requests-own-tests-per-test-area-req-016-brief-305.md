# ADR-0172: proof runs only the pull request's own tests, per test area (REQ-016, brief 305)

- Status: Proposed
- Date: 2026-10-29
- Deciders: maintainers
- Related: ADR-0167
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #305 (priority 1). In the pilot (#289, #287) proof ran the whole backend suite twice, about 13 to 25 minutes, close to its
900 s `proof_timeout`. A change of only front-end tests always read `unknown (no-test-files)`, because proof knows one command
(`project_tests`) and one set of test folders (`test_dirs`, `test_patterns`). The tests were written first: 25 of the 26 new cases of
`tests/kit/test_proof_areas.py` failed on the unchanged `proof.py` and `common.py` (first checkpoint of the pull request).

## Decision

1. **The `[proof]` table (answer 1).** `agk.toml` may have a `[proof]` table whose keys are test areas. Each area is a table with
   `dirs` (a list of folders), `patterns` (a list of file name globs), `command` (a shell template with `{files}`) and an optional
   `cwd`, the area's working folder inside the repository (default: the repository root). An area name is letters, digits, `-`
   and `_`. Any other key, a missing or empty list, an empty table or a `cwd` outside the repository is a refusal (exit 2) that
   names the setting (`proof`, `proof.<area>` or `proof.<area>.<key>`), never its value. Without the table proof works exactly as
   before: `project_tests`, `test_dirs`, `test_patterns`, and the `--json` object has no new key. With the table,
   `project_tests` is not read by proof (governance's project-tests step still runs it).
2. **One command per area (answer 2).** A test file of an area is a changed file under one of its `dirs` whose name matches one of
   its `patterns`; a file that matches two areas belongs to both. All the areas' test files are placed on the base worktree at
   once (added or modified copied, deleted removed, SPEC-0010 rule 10); then each area that has added or modified files runs its
   command, with only those files, on the base and on the head, each run within `proof_timeout`. An area with only deletions does
   not run. Each area's outcome is decided as SPEC-0010 rule 12. The whole result is `proven` only when every area that ran is
   proven; otherwise `unknown` (`timeout`) when any area timed out, else `not-proven` (`green-on-base` before `red-on-head`). No
   area with added or modified files is `unknown` (`no-test-files`); `Behaviour: unchanged` is `skipped`, as before.
3. **Files and the template (answer 3).** The command runs inside the area's `cwd` of each worktree (the base with the tests
   placed, and the head; the root when `cwd` is not set), and `{files}` is replaced by the area's files, each relative to `cwd` and
   quoted with `shlex.quote`, separated by spaces, so the folder is written once: `cwd = "backend", command = "uv run pytest
   {files}"` (Q-305-1, answered in the verdict on 73a14cf). A `cwd` that is not a folder of the head is refused, naming
   `proof.<area>.cwd`; a folder the base lacks is made empty in the base worktree, so the base run fails as the base it is. A
   command without `{files}` is refused: `the command of a proof area has no {files} (setting: proof.<area>.command)`.
4. **Output (answer 4).** The one line names each area that is not proven, in table order:
   `proof: not-proven (frontend: green-on-base)`, `proof: unknown (frontend: timeout after N s, setting: proof_timeout)`, several
   joined with `; `. The `--json` `reason` stays one word of SPEC-0010 rule 17, so the outcome step names of the `proof` job,
   `facts.py` and the product report read it unchanged (Q-305-2). `--json` gains `areas`: each area in table order with `name`,
   `files` (sorted; deletions included), `outcome` (null when it did not run), `reason` and `seconds` (whole seconds of its runs).
   `test_files` is the union of the areas' files.
5. **Tests (answer 5).** `tests/kit/test_proof_areas.py`, with plain-shell fake commands: one area; two areas, one red and one
   not; a front-end-only change; a red head; two areas not proven; a timeout in one area; no files; deletions only; no
   `project_tests`; the declaration; the command running inside `cwd` on both runs; a `cwd` missing from the head; a
   template without `{files}`; every malformed setting; and the unchanged path without the
   table. `tests/kit/test_proof.py` and `tests/kit/test_proof_timeout.py` are unchanged and pass.
6. **Flow mode.** Fragment `changelog.d/proof-areas.md`; no version bump; `kit/hashes.json` not edited (session rule 14).
   `docs/guides/existing-codebase.md` step 4 shows the table. SPEC-0010 is not edited (Q-305-3).

## Consequences

- A project that sets areas proves a small change with its own test files only, in minutes instead of two full suites.
- A front-end change with front-end tests is proven or not-proven, never `unknown (no-test-files)`.
- A test that depends on another test file the pull request did not change is still run, by the area's own command; a suite-wide
  effect (a fixture shared across the suite) is no longer exercised by proof, only by governance's project-tests step.
- A test file outside every area is not a test file for proof when the table is set.

## Residual

- 2026-10-29: Q-305-1 answered in the verdict on 73a14cf: the command runs inside `cwd`, and a `cwd` missing from the head is
  refused (decision 3).
- 2026-10-29: Q-305-2 answered in the verdict on 73a14cf: the area is named in the line and in `areas`; the `--json` `reason`
  stays one word and `facts.py` is unchanged (decision 4).
- 2026-10-29: Q-305-3 answered in the verdict on 73a14cf: no SPEC-0010 edit in this pull request; the reviewers file the
  amendment separately as proposed spec amendment 95.
- 2026-10-29: no project's real `[proof]` table was run; the first pilot that opts in reports its proof times (due 2026-12-15).

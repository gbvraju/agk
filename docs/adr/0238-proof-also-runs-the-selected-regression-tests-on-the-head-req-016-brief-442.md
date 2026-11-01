# ADR-0238: proof also runs the selected regression tests on the head, off until a person approves the spec change (REQ-016, brief 442)

- Status: Accepted
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0172, ADR-0185, ADR-0220, ADR-0230
- Requirements: REQ-016

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Proof (brief #305) runs only the pull request's own tests: red on the base, green on the head. A change that breaks a mapped
neighbour is caught only after the merge (#289, part 3). The regression selection of `impact.py` (brief #373) says which tests
guard the changed code, but nothing runs it. Proof's runs and outcomes are SPEC-0010 rules 11 and 12, an Approved spec, so the
behaviour is built off by default and the spec change is only a proposal, `docs/runs/proposed-spec-amendments-104.md`, until a
person approves it. Brief #442 gives the answers.

## Decision

1. **The setting (answer 2).** The `[testing]` table accepts `proof_regression`, a boolean, false by default. A value that is not
   a boolean is refused naming the setting (`testing.proof_regression`), never the value, by `impact.py`, so proof, the test plan
   and the pre-push gate refuse it alike. `impact.proof_regression(root)` reads it: false without the table or the key. The
   dictionary `testing_table` returns is unchanged. With false or absent, proof is exactly as today: no third run, and the line,
   `--json` and the manifest are unchanged.
2. **The third run (answer 1).** With `proof_regression = true` and a `[proof]` table, once the pull request's own runs are
   `proven`, proof runs on the head worktree, and never on the base, the test files that `impact.py` selects, grouped by `[proof]`
   area: each area's own command with only its selected files (`{files}`), in its `cwd`, in table order. Its failure makes the
   outcome `not-proven` with the reason `regression`, shown as `proof: not-proven (regression: <area>[, <area>])`. A run ended by
   `proof_timeout`, which applies to each run separately, makes the outcome `unknown` (`timeout`), shown as
   `proof: unknown (regression: <area>: timeout after <n> s, setting: proof_timeout)`; a timeout is named before a failure.
3. **Nothing extra (answer 1).** When the selection is `full`, proof runs nothing extra, since governance runs the full suite;
   when it selects nothing, or only documentation changed, nothing runs either. Each case names its reason in `--json` and in
   the manifest.
4. **Output (answer 3).** With the setting on, `--json` gains one key, `regression`: `runs` (each with `name`, `files`, `outcome`
   `passed`, `failed` or `timeout`, and `seconds`), `reason` (why nothing ran, else null) and `not_run` (selected files in no
   `[proof]` area). The manifest lists each regression run under `Ran` as `regression: <area>` with its command, folder, files
   and head seconds, and names under `Not run` why no regression ran and each selected file in no area.
5. **Tests first (answer 4).** `tests/kit/test_proof_regression.py`: regression green (`proven`), regression red
   (`not-proven (regression)`), `full` (nothing extra), nothing selected, the key off or absent (unchanged), the third run on the
   head only, a timeout, a selected file in no area, no `[proof]` table, own tests not proven, the manifest, and the setting's
   refusals and default.

## Consequences

A team that turns the setting on, after a person approves the amendment, sees a broken mapped neighbour as a red proof before
review instead of a red default branch after the merge. Proof takes longer by the selected tests' time on the head. Nothing
changes for a team that leaves it off, and this repository leaves it off.

## Residual

- 2026-10-31: Q-442-1: the selected set may hold a test file of the pull request itself when a `tests` glob matches it; it runs
  again in the third run, as the selection says. The conservative reading runs the selection as given.
- 2026-10-31: Q-442-2: without a `[proof]` table, run 2 is `project_tests` on the head, which already runs every test, so a
  third run would repeat it; proof runs nothing extra and says `no [proof] table: project_tests ran every test on the head`.
- 2026-10-31: Q-442-3: the third run is made only when the pull request's own runs are `proven`; any other outcome already
  stands and a third run could not change it (`skipped`, `unknown` and `not-proven` are kept as they are). Accepted by the
  conductor's verdict on 4a45ff8: a pull request with no test files stays `unknown (no-test-files)` with no third run, and
  amendment 104 says so. The same verdict (finding 1): a skipped run names its skip, `not run (draft)`, `not run
  (status-only)` or `not run (Behaviour: unchanged)`, since the own tests did not run; "not proven" is kept for an own
  outcome that ran.
- 2026-10-31: Q-442-4: a selected file that lies in no `[proof]` area has no command that takes it; it is listed under
  `not_run` and never run, and the outcome does not depend on it.
- 2026-10-31: Q-442-5: the amendment number 104 is the next free one; the brief named none.
- 2026-10-31: `test_plan.py`, `docs/guides/testing.md` and `.github/workflows/proof.yml` are outside the brief's `Touches:` line
  and are unchanged; the workflow's outcome steps already take the reason from proof's output.

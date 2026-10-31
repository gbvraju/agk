# Proposed spec amendments 104 (SPEC-0010; REQ-016)

Date: 2026-10-31 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for ADR-0238
(brief #442), which stays `Proposed` for the maintainers' decision. The path: `docs/specs/0010-proof-checks.md`. The number 104 is
the next free one (Q-442-5). It needs a person's `Approve: SPEC-0010`; no session posts it. Until then the setting
`[testing] proof_regression` stays false (its default), and no run of this repository turns it on.

1. **SPEC-0010 rule 11, the runs**, gains at its end: "Run 3, only with `[testing] proof_regression = true` in `agk.toml` (a
   protected setting, changed only with an ADR in the same pull request), a `[proof]` table, and runs 1 and 2 `proven`: on the
   head worktree, never on the base, the test files that `impact.py` selects for the change, grouped by `[proof]` area, each
   area's own command with only its selected files, in its `cwd`, in table order. When the selection is `full`, proof runs nothing
   extra, since governance runs the full suite; when it selects nothing, nothing runs. Without a `[proof]` table run 2 is
   `project_tests` on the head, which already runs every test, and nothing extra runs. A selected file in no `[proof]` area is
   listed as not run. `proof_timeout` applies to run 3 separately (rule 15). With the setting false or absent there is no run 3
   and nothing in proof's output changes."
2. **SPEC-0010 rule 12, the outcomes**, gains, after `proven` is decided and before it is reported: "`unknown` (`timeout`) when
   run 3 exceeds `proof_timeout`, shown as `proof: unknown (regression: <area>: timeout after <n> s, setting: proof_timeout)`;
   `not-proven` (`regression`) when run 3 failed in one or more areas, shown as `proof: not-proven (regression: <area>[, ...])`.
   A timeout is named before a failure. Otherwise the outcome stays `proven`."
3. **SPEC-0010 rule 13, output and exit**, gains: "With the setting on, `--json` has one more key, `regression`: `runs` (each
   with `name`, `files`, `outcome` `passed`, `failed` or `timeout`, and `seconds`), `reason` (why nothing ran, else null) and
   `not_run`. `regression` is one more value of `reason`. The exit statuses are unchanged."
4. **SPEC-0010 rule 14, what it proves**, gains: "*With run 3 it also proves* that the tests mapped to the changed code pass on
   the head. *It does not prove* that the `[testing]` map is complete: a neighbour that no entry maps is not run."
5. **Tests (rule 19).** `tests/kit/test_proof_regression.py`: regression green, regression red, `full`, nothing selected, the
   setting off or absent, run 3 on the head only, a timeout, a selected file in no area, no `[proof]` table, own tests not
   proven, the manifest, and the setting's refusals.

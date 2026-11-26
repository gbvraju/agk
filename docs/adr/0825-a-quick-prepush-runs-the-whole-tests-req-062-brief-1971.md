# ADR-0825: A quick prepush runs the whole tests, and the list gains two (REQ-062)

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1971, ADR-0186 (prepush), ADR-0185 (test_plan), ADR-0227 (the regression run under the lock),
  ADR-0306 (the secret scan also with `--quick`), ADR-0422 (selected runs in workers), ADR-0440 (`local_full`),
  ADR-0650 (the whole tests), ADR-0755, ADR-0777, ADR-0780, ADR-0536 and ADR-0605 (the local record, kept), #1950,
  #1959, #1963, plan #661
- Requirements: REQ-062

Protected classes: `scripts/agk/`, `agk.toml`, `config/`, `kit/`, `tests/kit/`

## Context

`prepush.py --quick` returned `skipped` before it read the plan, so a builder on a small machine ran no whole-repository
test before a push. On 25 Nov three pull requests (#1950, #1959, #1963) each failed a whole test only in CI's full
governance run, one round and one fix head each. Two of the three tests were already in `[testing] whole_tests`; the
other two (`test_common_option_pairs.py`, `test_playbook_default.py`) were in no list. The owner's word (2026-11-26, the
steward chat, quoted as data): "Go ahead and prioritize the parked briefs and start asking conductor implement them".

## Decision

1. With `--quick`, the tests step reads `[testing]` first (a bad `whole_tests` is refused naming
   `setting: testing.whole_tests`), runs `test_plan.py --json` as today, then `impact`, and runs only the files of its
   `whole` list through the first `[proof]` area each lies in: one run per area, named `whole` (`whole-<area>` when two
   areas hold them), with `selected_workers`, under the heavy-step lock (`--no-lock` as today) and `proof_timeout`.
   Each prints `prepush: tests whole ok|FAIL (<s>s): listed in testing.whole_tests`; the step text is
   `--quick: the whole tests only`. Proof's runs, the mapped and named tests and the full suite stay skipped.
2. No `[testing]` table, no `whole_tests` key, a documentation-only change or no whole file in the head: the step is
   `skipped` with no command, its text naming the reason. A whole file in no area is `not run (in no [proof] area)`.
3. The record holds the runs under the set `whole`; `evidence.py:planned_runs` rebuilds that set from
   `prepush.quick_sets`, so a quick record is checked as any other run, and a skipped quick step is read as today.
4. `test_plan.py` prints `quick: prepush --quick runs these <k> whole tests` after the `whole:` lines and its JSON gains
   `quick_whole`; with none, neither.
5. The kit's `whole_tests` gains `tests/kit/test_common_option_pairs.py` and `tests/kit/test_playbook_default.py`
   (Q-SG-1: listed); session rule 31 and the builder's runtime prompt say a quick prepush runs the whole tests.

## Consequences

A quick prepush in this repository costs about 80 s more on a 2-CPU machine with two workers; the three failures of
25 Nov fail before the push. CI's full run stays the gate. A project whose `agk.toml` leaves `whole_tests` commented
sees no change. No workflow, check name, label or setting changes.

## Residual

A whole test nobody listed is still found only by the push run (SPEC-0055 rule 11); the check that finds one stays
SPEC-0055's open item (Q-SG-3). Per-path whole tests are not built (Q-SG-2).

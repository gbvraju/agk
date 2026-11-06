# ADR-0320: The pre-merge check runs the kit tests that read the whole tree (REQ-046, brief 667)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0297, ADR-0273, ADR-0310, SPEC-0039
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `agk.toml`, `tests/kit/`, `tests/kit_dev/`

## Context

ADR-0297 runs governance on the would-be merge before `merge_cleared.py` merges. Twice on
2026-11-06 the default branch still turned red. In #657, #638 and #648 were each green alone,
and once both had merged `tests/kit/test_rule_budget.py` failed. In #659 the same happened with
#644 and #648. The budget test reads the whole tree, and so do the testing map and manifest
tests. `make governance` runs none of them, so the check before the merge could not see the
failure. The ADR number and amendment 132 of SPEC-0039 were reserved for brief #667 in the brief.

## Decision

1. **The tests (amendment 132, rule 6).** After governance passes on the would-be merge, the
   command runs the test files of `[testing] pre_merge_tests` in the same detached worktree. The
   setting is read from `agk.toml` on the default branch. The run uses the heavy lock with the
   same timeout and `env -i` with `PATH`, `HOME`, `AGK_KIT_TESTS=1` and
   `PYTHONDONTWRITEBYTECODE=1` only, then `<python> -m pytest -q --rootdir <worktree> <the
   files>`. pytest reads the configuration file it finds above the files. The brief's
   `-c tests/kit/pytest.ini` is left out: installed code names no kit test path (lean install,
   ADR-0052). A failure holds with `held: the merge with the default branch fails pre-merge
   tests (<file>::<test>)`, exit 3, and nothing is merged, recorded or filed. The hold names
   the first failing test, or `heavy lock` or `pytest` when no test is named. The run after the
   merge is unchanged.
2. **The setting.** `pre_merge_tests` is a non-empty list of file paths inside the repository,
   with no globs. When the key is absent, no test runs, as before. This repository's `agk.toml`
   sets it to the brief's list: `tests/kit/test_rule_budget.py`,
   `tests/kit_dev/test_intelligent_testing.py` and `tests/kit_dev/test_kit_manifest.py`. The
   kit's tests are not installed in a project, and installed code names no kit test path (lean
   install, ADR-0052), so the list lives in the setting and not in the code. A malformed value
   is refused before anything runs, naming `testing.pre_merge_tests`. A listed name that is not
   a file of the merge holds, naming the same setting. `impact.testing_table` accepts the key and refuses a listed name that is not a file
   of the checkout.
3. **Fail-closed.** Any exit other than 0 holds, including a missing pytest, no test collected or
   an interrupt. `governance not finished` still covers an exception during the check.

## Consequences

A merge that is green alone and red together on the rule budget, the testing map or the manifest
is held before it merges. The conductor's next pass merges it once the head is updated. The three
files take about 2.5 s on a merge of this repository (53 tests), so the `merge-cleared` lock is
held about that much longer. With `auto_merge` off nothing changes.

## Residual

- 2026-11-06: an installed project gets no pre-merge test unless it sets the key (Q-667-1, due
  2026-12-31).
- 2026-11-06: a test that reads the whole tree and is not on the list is still unseen before the
  merge; the run after the merge (ADR-0273) and CI still catch it (due 2026-12-31).

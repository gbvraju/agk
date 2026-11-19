# ADR-0650: A change runs the whole-kit tests on its pull request and on the would-be merge (REQ-062)

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: SPEC-0055, SPEC-0039, amendment 186, amendment 187, brief #1548, ADR-0440, ADR-0359, #1516, #1527, #1529, #1532, #1546, #1547, plan #661
- Requirements: REQ-062, REQ-046

Protected classes the builds of this decision change: `scripts/agk/`, `tests/kit/`, `agk.toml`, `kit/`. This pull
request changes none of them.

## Context

On 2026-11-19 the default branch was red twice, 259 of the 800 minutes from 02:49Z to 16:09Z, and no pull request
merged in either window. #1516 (6f7288da) selected 11 test files and #1527 (0d4ba3a3) selected 5, replayed with
`test_plan.py --base <merge>~1 --head <merge>`; none of the 4 tests that then failed on the push run was among them
(`test_distribution.py` twice, `test_playbook.py`, `test_installed_imports.py`). Each of those tests reads every
installed, tracked or kit file and asserts one rule over all of them, but `impact.py` selects only the tests of the
`[[testing.map]]` entries that match a changed file and of the files that import it, one level, and maps such a test to
a few scripts only. A change of only `*.md` files selects nothing (`impact.is_doc`), installed agent files included.
The would-be merge of `merge_cleared.py` runs governance and `[testing] pre_merge_tests` (three files in the kit, none
of the four). The full suite runs only on the push to the default branch, after the merge.

The options, with the costs measured on the runs above (CI) or estimated `(verify)`:

| Option | What runs | Cost | Catches the two of 2026-11-19 before the merge |
| --- | --- | --- | --- |
| (A) a whole-test list added to every pull request's selection | `prepush.py`, `project_tests.plan`, `test_plan.py` | about 15 to 60 s per pull request run on CI `(verify)`, at most about 30 Actions minutes a day at about 28 runs; 1 to 3 minutes per prepush on a 2-core laptop `(verify)` | 2 of 2; misses a whole test nobody listed |
| (B) the same list on the would-be merge, beside `pre_merge_tests` | `merge_cleared.py` | 0 Actions minutes; 1 to 3 minutes per merge under the heavy lock `(verify)`, about 13 merges a day | 2 of 2, and a break that only the newer default branch shows; alone, late (after the accept) |
| (C) the full suite on the would-be merge | `merge_cleared.py` | 11 to 15 minutes per merge on 4 workers, about twice on a laptop `(verify)`; 2.5 to 6.5 hours of serial merge time a day | 2 of 2 and unknown classes; too slow for the merge rate, and the day's two flaky timing tests would have held two merges |
| (D) the full suite on every pull request (`pr_tests = "full"`) | the `Tests of the checks` step | 11 to 15 more Actions minutes a run, 5 to 7 Actions hours a day; first feedback from about 1 to about 13 minutes | 2 of 2; the cost the owner set `selected` to avoid |
| (E) a nightly full run | a schedule | about 15 Actions minutes a day | 0 of 2: the push run already finds each in 11 to 15 minutes |

A catch-all `[[testing.map]]` entry (`code = "**"`) would select the list, but it would cover every file, so the
fallback of SPEC-0055 rule 6 would never apply and a file whose entries select no existing test would no longer be
full. The list needs its own key.

## Decision

1. Options (A) and (B), with one list. `[testing] whole_tests` (the name is Q-1548-1's reading) is an optional list of
   test file paths, each a file inside the repository, no globs, forward slashes; a bad entry is refused naming
   `setting: testing.whole_tests`, never the value (amendment 186, SPEC-0055 rules 2 and 6).
2. The list is added to every pull request's selection, under every profile, after the map, importers and unmapped
   steps, when the change is not documentation only, and also when a change of only `*.md` files includes an installed
   file of the kit manifest or a protected path. Each file prints `whole: <file>`. It only adds tests: it never counts as
   covering a changed file, so SPEC-0055 rule 6's fallback, `full`, `unmapped` and `always_full` are unchanged. A change
   under `docs/` only selects nothing, as today (Q-1548-3).
3. The merge check runs `whole_tests` with `pre_merge_tests` on the would-be merge, the union in one pytest call, each
   file once, with the same hold line (amendment 187, SPEC-0039 rule 6). Both lists stay (Q-1548-4).
4. In local mode (`execution = "local"`, or the open local-mode record issue), `local_full = "ci"` no longer leaves the
   full suite to a CI run that never happens: the run is full there, as with `local_full = "local"`, and prints one line
   naming the setting (Q-1548-5).
5. The kit's first list is the 15 test files that brief #1548 read from the code; a test is a whole test when it reads
   every file of a class (installed, tracked, kit, or a manifest of them) and asserts a rule over all of them, and a new
   such test joins the list in the pull request that adds it (Q-1548-2). Build (c) measures the list and may trim it.
6. A project sets its own list; the kit never fills it. A playbook may propose a project's whole tests as a proposal
   that `engines.py` prints, never written (Q-1548-6).
7. Options (C), (D) and (E) are not chosen; `pr_tests` and a project's own schedule already offer (D) and (E), and
   neither changes. A forge-button merge skips the merge check, as today (Q-1548-7, brief #1539's intake).
8. The work is three builds, each filed by the `brief` skill with a Settings section (lettered (k) to (m) in amendment
   186, after SPEC-0055 rule 15's (a) to (j)): (a) the key, its checks and the
   selection in `impact.py`, `project_tests.py`, `prepush.py` and `test_plan.py`, with decision 4; (b) the merge
   check's union in `merge_cleared.py`; (c) the kit's own list in `agk.toml`, `check_kit_tests.py`'s non-empty check,
   `doctor.py`'s count, the template, the guide, and the corrected name of the job beside `local_full`.

## Consequences

A change that can break a whole-kit test runs it on its pull request and again on the would-be merge, so #1516 and
#1527 would each have been red on their pull requests. With the key absent, every project runs as today. A whole test
nobody listed is still found only by the push run, as a selection miss (SPEC-0055 rule 11). A build that cites this ADR
with `Covered-by:` once it is Accepted may change only the classes named above.

## Residual

- 2026-11-19: the added time of the list on CI and on a laptop is an estimate `(verify)`; build (a) measures it, and the
  goal is at most 90 s on a pull request run on CI (due 2026-12-31).
- 2026-11-19: membership is by a person's judgement in the pull request that adds a test; a check that finds an unlisted
  whole test is not decided here (due 2026-12-31).
- 2026-11-19: a forge-button merge skips the list as it skips `pre_merge_tests` (brief #1539's intake, due 2026-12-31).

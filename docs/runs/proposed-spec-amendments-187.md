# Proposed spec amendments 187 (SPEC-0039; REQ-046, REQ-062)

Date: 2026-11-19 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0650 (brief #1548), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. Brief #1548 reserved
amendment 187. This file proposes the lines and does not edit the spec; the owner approves the amendment. Amendment 186
proposes the key and the pull request's half (SPEC-0055 rules 2, 6a and 6b).

The sentence (brief #1548): "A change that can break a test which reads the whole kit runs that test on its pull request
and on the would-be merge, so a green pull request never turns the default branch red for a test its selection left out,
in the kit and in every project."

## Why

The would-be merge of rule 6 runs governance (the checks, no tests) and then `[testing] pre_merge_tests`, in the kit
`tests/kit/test_rule_budget.py`, `tests/kit_dev/test_intelligent_testing.py` and `tests/kit_dev/test_kit_manifest.py`
(`agk.toml` at 359edcd3). None of the four tests that failed on the default branch after #1516 and #1527 on 2026-11-19
is among them (amendment 186, Why). A pull request's selection runs on its own head, and the default branch may have
moved since; the would-be merge is the one run on the tree that will be the default branch. In local mode it is the
project's last run before its default branch.

Read in the code at 359edcd3: `merge_cleared.merge_check` builds the would-be merge, runs `run_governance` in a detached
worktree, then `impact.pre_merge_names` and `run_tests` (one pytest call over the names, under the heavy lock and `env
-i`), and holds with `TESTS_FAIL` naming the first failing test; `pre_merge_setting` checks the `[testing]` table of the
default branch before anything runs. `merge_check_once` keeps a result per head, default branch, body and `[testing]`
table (`checked_key`), so a changed list is judged again.

## Items

1. **Rule 6 gains, after "naming the first failing test (or `heavy lock` or `pytest`)".** "The same run also takes the
   test files of `[testing] whole_tests` (SPEC-0055 rule 6a, amendment 186) from `agk.toml` on the default branch: the
   union of `pre_merge_tests` and `whole_tests`, each file once, in the order `pre_merge_tests` then `whole_tests`, in one
   pytest call, held with the same line `held: the merge with the default branch fails pre-merge tests
   (<file>::<test>)`, exit 3, and nothing is merged, recorded or filed. Without either key the run has no tests, as
   today without `pre_merge_tests`. A malformed `whole_tests` is refused before anything runs, naming
   `testing.whole_tests`, and a listed name that is not a file of the merge holds naming `testing.whole_tests`, as for
   `pre_merge_tests`; a hold names the setting, the file and the test, never a value. The once-per-head result (ADR-0570
   decision 4) is keyed by the whole `[testing]` table already, so a changed list is judged again."
2. **Rule 6 is otherwise unchanged:** the would-be merge, the governance run, the heavy lock, `env -i` with its four
   variables, the hold lines, the REST merge with the pinned sha, the governance run after the merge and the red-branch
   path. SPEC-0055 rule 10's `main` levels in the merge check in local mode (`Q-S0055-12`, its build (g), not built at
   359edcd3) stay a separate build; when it lands, those levels run with the union of item 1 (the reading of
   `Q-1548-4`: no list replaces another).
3. **Rule 11, the guide.** "`docs/guides/auto-merge.md` says that the would-be merge runs `pre_merge_tests` and
   `whole_tests`, and that a forge-button merge runs neither (`Q-1548-7`)."
4. **Rule 12, the builds, gains** "build (l) of amendment 186: the union of item 1 in `merge_cleared.py`, `tests/kit/`,
   `Covered-by: ADR-0650` once it is Accepted; `Depends-on` amendment 186's build (k), which adds the key and its check
   in `impact.py`."
5. **Tests gains:** "Rule 6's union, on an invented repository (`example.com`) with saved git trees and no network: both
   keys (one pytest call, each file once, a file in both run once); only `whole_tests`; only `pre_merge_tests` (as
   today); neither (no test run); a listed whole test that passes on the head and fails on the would-be merge (held,
   the line naming the file and test); a malformed `whole_tests` (refused before the would-be merge is built, naming the
   setting); a listed name missing from the merge (held, naming the setting); a changed list on the default branch
   between two runs on one head (judged again); `heavy lock` and `pytest` failures named as today. REQ-046, REQ-062."
6. **Proof gains:** "On a scripted repository whose default branch moved after a pull request's head was tested, with
   `whole_tests` naming an invented whole test that the move breaks for that head: the merge check holds with
   `fails pre-merge tests (<file>::<test>)` and merges nothing; with the list removed it merges. Before: it merges, and
   the push run is red."
7. **The settings, each with its impact, traced:**

   | Setting | Impact |
   | --- | --- |
   | `[testing] whole_tests` absent | unchanged in every mode |
   | `[testing] pre_merge_tests` | unchanged; both lists run, each file once |
   | `[flow] auto_merge`, `auto_merge_method` | the merge check runs only on the guarded path; off, nothing here runs, as today |
   | `[flow] merge_queue` | a queued head is checked by the same run before it is queued, as today `(verify: build (l) reads the queue path)` |
   | `[flow] max_behind_merges` | unchanged; the behind hold is read before the would-be merge |
   | `execution`, local mode | the run is the project's last before its default branch (no CI push run in local mode) |
   | `--owner`, and brief #1539's owner's word | both run the same merge check, so both run the list |
   | `review_mode`, `pr_mode` | no change |
   | `forge = "files"` (personal mode) | no merge check; the floor runs the whole `test_command` |
   | `workers`, `AGK_TEST_WORKERS` | not read by the merge check (one pytest call, as today) |
   | Windows | the merge check on Windows follows brief #1540; entries are posix paths |
   | a forge-button merge | skips the merge check and the list, as it skips `pre_merge_tests` (`Q-1548-7`) |

## Questions (brief #1548)

The questions are those of amendment 186 (`Q-1548-1` to `Q-1548-9`); this amendment relies on `Q-1548-4` (both lists
stay, each file once) and `Q-1548-7` (a button merge skips the list, unchanged here).

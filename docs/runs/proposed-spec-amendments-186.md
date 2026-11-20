# Proposed spec amendments 186 (SPEC-0055; REQ-062)

Date: 2026-11-19 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0650 (brief #1548), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0055-the-right-tests-for-each-stack-run-at-the-right-time-by-a-map-that-learns.md`. Brief #1548 reserved
amendment 186. This file proposes the lines and does not edit the spec; the owner approves the amendment. Amendment 187
proposes the merge check's half (SPEC-0039 rule 6).

The sentence (brief #1548): "A change that can break a test which reads the whole kit runs that test on its pull request
and on the would-be merge, so a green pull request never turns the default branch red for a test its selection left out,
in the kit and in every project."

## Why

Measured on the default branch at 359edcd3 (2026-11-19), the brief's figures reproduced (session rule 19) with
`python3 scripts/agk/test_plan.py --base <merge>~1 --head <merge>` in a worktree of each merge commit:

- #1516 at 6f7288da: `regression: 11 test files selected` (`test_always_full_infra.py`, `test_architect_guard.py`,
  `test_guard_plugin_forms.py` and the eight `test_conductor_guard*.py`); its push run failed
  `test_distribution.py::test_ac3_only_the_resolver_names_the_plugin_variable`,
  `test_distribution.py::test_ac3_no_law_file_depends_on_the_plugin` and
  `test_playbook.py::test_ac1_the_role_file_and_guard_name_no_plugin_variable`, none of the 11.
- #1527 at 0d4ba3a3: `regression: 5 test files selected` (`selected: scripts/agk/personal.py -> 4 tests (0 by
  importers)` plus `test_always_full_infra.py`); its push run failed
  `test_installed_imports.py::test_a_every_installed_script_imports_only_installed_modules`, not among the 5.

The default branch was red 94 and 165 minutes, 259 of the 800 minutes from 02:49Z to 16:09Z, with no merge in either
window (the brief's reading of the push runs, not re-read here).

Why the selection missed, read in the code: `impact.select` takes the tests of the `[[testing.map]]` entries whose `code`
matches a changed file and of the files that import it, one level (`test_map.importers_of`); under `balanced` an
unmapped file selects the tests that name it (rule 6). A test that reads every installed file is mapped to a few scripts
only (`test_installed_imports.py` to `tree_walk.py` and `plan_names.py`), and a new import edge from a changed file is
not read. A change of only `*.md` files or files under `docs/` is documentation only (`impact.is_doc`) and selects
nothing, including an installed file such as `.claude/agents/architect.md`, which is in the kit manifest's `verbatim`
list and which `test_playbook.py` reads. A catch-all `[[testing.map]]` entry is not the fix: it would cover every file,
so rule 6's fallback would never apply (ADR-0650, Context).

## Items

1. **Rule 2 gains one sentence, after "add tests and never remove one".** "The whole tests of rule 6a are added the same
   way: they only add tests and never make a changed file covered."
2. **Rule 6a, the whole tests (new).** "`[testing] whole_tests` (optional; `Q-1548-1`) is a list of test file paths,
   each a file inside the repository, relative, with forward slashes and no glob character (`*`, `?`, `[`); a value that
   is not a non-empty list of such strings, an entry with a backslash, an absolute path, a `..` part or a path outside
   the repository, and an entry that is not a file of the tree are each refused before anything runs, naming
   `setting: testing.whole_tests`, never the value, as `pre_merge_tests` is. A whole test is one that reads every file of
   a class (installed, tracked, kit, or a manifest of them) and asserts a rule over all of them (`Q-1548-2`). `impact.py`
   adds the listed files to the selection of every pull request whose change is not documentation only, after the map,
   importers and unmapped steps, under every profile, and also to a change of only `*.md` files when one of them is an
   installed file (a path of the kit manifest's install lists) or a protected path (`config/protected-paths.txt`); a
   change only under `docs/` selects nothing, as today (`Q-1548-3`). Each added file prints one line `whole: <file>` in
   the selection, after the `selected:` and `unmapped:` lines. The list never counts as covering a changed file, so the
   fallback of rule 6, a full run for an unmapped file no test names, `always_full` and `full_when_share` read the
   selection as they do today; the listed files count among the selected files of the share, so a selection reaches the
   share sooner, never later. A listed file runs through the `[proof]` area it lies in, as a selected file does; a listed
   file in no area is `not run (in no [proof] area)` on a developer's machine and fails the CI test step naming the
   setting, as a linked level does (rule 7). A file in both the list and the selection runs once."
   - AGK itself: build (c) sets the kit's first list, the 15 files of brief #1548 (`tests/kit/test_installed_imports.py`,
     `tests/kit_dev/test_distribution.py`, `tests/kit_dev/test_playbook.py`, `tests/kit_dev/test_kit_manifest.py`,
     `tests/kit_dev/test_kit_hashes.py`, `tests/kit_dev/test_kit_hashes_rows.py`, `tests/kit/test_licence_headers.py`,
     `tests/kit_dev/test_licence_notice.py`, `tests/kit/test_check_neutrality.py`, `tests/kit/test_plugin_snapshot.py`,
     `tests/kit/test_isolated_mode.py`, `tests/kit/test_output_encoding.py`, `tests/kit/test_windows_install.py`,
     `tests/kit/test_rule_budget.py`, `tests/kit_dev/test_intelligent_testing.py`), measured and possibly trimmed; a new
     whole test joins the list in the pull request that adds it, and `kit/templates/runtime/builder.txt` says so (build
     (m)). `check_kit_tests.py` checks the kit's list is not empty.
   - Project, GitHub: the project sets its own list (architecture, contract, licence or layering tests); the kit never
     fills it. Its `Project tests` step runs the list through `project_tests.plan`.
   - Project, local: `prepush.py` step 5 runs the list; the merge check runs it again on the would-be merge (amendment
     187), the project's last run before its default branch.
   - Project, personal: unchanged; the floor of SPEC-0041 rule 18 runs the whole `test_command` before the push, and the
     gate's quick run adds the list as a selection does.
3. **Rule 6b, `local_full` where no CI proof job runs (new; `Q-1548-5`, answered).** "Only where no CI proof job runs
   on the pull request, `local_full = "ci"` does not leave the full suite to CI, because no CI run follows:
   `prepush.left_to_ci` keeps the full run and prints one line `tests: full suite runs here (setting: testing.local_full;
   no CI proof job)`. Where a CI proof job runs on the pull request, in local mode too, `local_full = "ci"` leaves the
   full suite to CI as today. No CI proof job runs when the one local-mode record issue is open (CI blocked, session rule
   30) or when the repository has no proof workflow (`.github/workflows/proof.yml`); `execution = "local"` alone does not
   turn the rule on (`Q-1548-10`). The comment beside `local_full` in `agk.toml` and `prepush.py`'s docstring and its line
   `tests: full suite left to CI's proof job` name the job that runs it: in the kit, governance's `Tests of the checks`
   step (not `proof.yml`, which runs the pull request's own test files red then green); in a project, its `Project
   tests` step."
4. **Rule 15, the builds, gains** "(k), (l) and (m) of amendment 186 and 187", as listed below.
5. **Tests gains:** "Rule 6a, each on an invented tree (`example.com`), with no network: a docstring-only change of an
   installed script (the #1516 replay selects the list, and an invented naming test fails on the pull request); a new
   or changed installed script that imports an experimental-only module (the #1527 replay selects an invented
   installed-imports test, which fails); a change to an experimental-only file (the list is selected); a changed script
   with no map entry (rule 6's fallback still runs, the list is added, and the file stays unmapped); a change of
   `impact.py` (`always_full` as today); a change of `whole_tests` in `agk.toml` (the new list is selected, and
   `test_always_full_infra.py`); a change of only an installed `*.md` file such as an agent file (the list is
   selected); a change of only a protected `*.md` file (the list is selected); a change only under `docs/` (nothing);
   the key absent (the selection is byte for byte today's); each refused entry (missing file, glob, absolute path,
   `..`, a backslash, a non-list, an empty list; each names the setting, never the value); a file in the list and the
   selection (run once); a listed file in no `[proof]` area (`not run` locally, a CI failure naming the setting);
   `fast`, `balanced` and `thorough` (the list is added under each; `thorough` is full); `pr_tests = "full"` (inside the
   full run); `full_when_share` reached by the list's files (full). Rule 6b: `local_full = "ci"` with an open record issue
   and with no proof workflow (full, the line printed), and with `execution = "local"` while a proof job runs and in
   GitHub mode (left to CI as today, the corrected job name). REQ-062."
6. **Proof gains (the measured goal):** "On the kit with the first list: `test_plan.py --base 6f7288da~1 --head
   6f7288da` selects `tests/kit_dev/test_distribution.py` and `tests/kit_dev/test_playbook.py`, and `--base 0d4ba3a3~1
   --head 0d4ba3a3` selects `tests/kit/test_installed_imports.py`, each with a `whole:` line; a pull request run of the
   kit whose change is only an installed `*.md` file runs the list; the added time of the list on a pull request run is
   printed and is at most 90 s on CI `(verify)`. The same on a project made from `kit/templates/agk.toml` with one
   invented whole test. Before: 0 of the 3 files selected on both replays."
7. **Residual gains:** "2026-11-19: a whole test nobody listed is found only by the push run, as a selection miss (rule
   11); a check that finds an unlisted whole test is not decided here (due 2026-12-31)." and "2026-11-19: the time the
   list adds on a 2-core laptop is an estimate of 1 to 3 minutes `(verify)`; build (k) measures it (due 2026-12-31)."
8. **Contexts**, the `kit` entry gains: "`[testing] whole_tests` in `impact.py`, read by `prepush.py`,
   `project_tests.py`, `test_plan.py`, `doctor.py` and the merge check, all installed in every project, and the kit's
   own list in `agk.toml`"; `github`: "no workflow, ruleset or required-check change: `Tests of the checks` and `Project
   tests` already run the plan; the list adds files to it; no new GitHub API call"; `local`: "prepush and the merge check
   run the list in the builder's and the conductor's checkouts, LF and CRLF alike; rule 6b closes the gap of `local_full
   = "ci"` where no CI proof job runs"; `personal`: "unchanged: the floor runs the whole test command"; `stacks`: "the list holds a project's own
   test file paths, for any stack, run through its `[proof]` areas".
9. **The settings, each with its impact, traced:**

   | Setting | Impact |
   | --- | --- |
   | `whole_tests` absent | nothing changes in any mode (rule 2); every project today |
   | `profile` | `fast`, `balanced` and `thorough` all add the list; `thorough` is full anyway |
   | `pr_tests` | `full`: the list is inside the full run; `selected`: it is added to the selection |
   | `always_full` | a match stays full; the list changes nothing there |
   | `full_when_share` | the list's files count among the selected files (15 of 542 tracked test files in the kit), so a selection can tip into full sooner, never later |
   | `local_full` | `"local"`: unchanged; `"ci"`: the list runs locally beside the mapped tests; where no CI proof job runs on the pull request, the full suite runs here (rule 6b) |
   | `execution`, the local-mode record issue | `execution = "local"` alone changes nothing; an open record issue (no CI proof job) turns rule 6b on |
   | `pre_merge_tests` | unchanged; the merge check runs both lists, each file once (amendment 187) |
   | `map_source` curated or generated | the list is separate from the map and read the same way under both |
   | playbook maps (`config/playbooks/*.toml`, `engines.py`) | a playbook may propose a project's whole tests, printed by `engines.py` as a proposal, never written to `agk.toml` (`Q-1548-6`) |
   | `[[testing.map]]`, `[[testing.links]]`, `docs/runs/test-links.toml` | unchanged; a missing entry still falls back as rule 6 says; the list never covers a file |
   | `[proof]` areas and levels | a listed file runs through its area and level; in no area: `not run` locally, a CI failure, naming the setting |
   | `workers`, `AGK_TEST_WORKERS` | the list runs in the same workers; a slow laptop sets its own count |
   | `auto_merge`, `[flow] max_behind_merges` | the merge check is the only merge path that runs the list; a forge-button merge skips it, as it skips `pre_merge_tests` today (`Q-1548-7`) |
   | `review_mode` solo or team, `pr_mode` strict or flow | no change; a hold names the file and test only |
   | `forge = "files"` (personal mode) | the floor runs the whole `test_command` before the push; the list changes nothing there |
   | `layout = "plugin"` | test paths are the project's; no plugin path enters the list |
   | Windows | entries are forward-slash paths, compared as posix; a backslash entry is refused naming the setting; the merge check on Windows follows brief #1540 |

## The builds

Each tests first, about 250 changed lines or fewer, each filed later by the `brief` skill with `Covered-by: ADR-0650`
once it is Accepted, and a Settings section:

- (k) the key and its checks in `impact.testing_table`, the selection in `impact.select`, and `project_tests.plan`,
  `prepush.py` step 5 and `test_plan.py` printing and running it through their `[proof]` areas, with rule 6b;
  `tests/kit/`. The brief's build (a).
- (l) the merge check's union in `merge_cleared.py` (amendment 187). The brief's build (b).
- (m) the kit's own list in `agk.toml`, `check_kit_tests.py`'s non-empty check, `doctor.py`'s count line and its refusal
  of a bad entry by its place, `kit/templates/agk.toml` (the key, commented out), one paragraph of `docs/guides/testing.md`
  and the corrected job name beside `local_full`. The brief's build (c). `Depends-on` (k).

## Questions (brief #1548), each with the reading this proposal takes

- Q-1548-1: the key's name. `whole_tests`, until the maintainers name it.
- Q-1548-2: what makes a test a whole test. It reads every file of a class (installed, tracked, kit, or a manifest of
  them) and asserts a rule over all of them; the kit's list starts with the 15 files above, and a new such test joins
  the list in the pull request that adds it.
- Q-1548-3: run the list on a change of only `docs/` files? No; the governance checks already read every document
  (`check_neutrality`, `check_licence_notice`), and a `docs/` file is not installed.
- Q-1548-4: should the list replace the kit's three `pre_merge_tests`? No; both stay, each file runs once.
- Q-1548-5: in local mode `local_full = "ci"` leaves the full suite to a CI run that never happens. Answered by the
  maintainer on #1549 (comment 7016265488, 2026-11-19, quoted as data): "amendment 186 approved, with rule 6b only where
  no CI proof job runs on the pull request". Rule 6b applies only there; where a proof job runs, `local_full = "ci"`
  leaves the full suite to CI as today.
- Q-1548-6: may a playbook propose a project's whole tests? Printed as a proposal only, never written.
- Q-1548-7: a forge-button merge skips the merge check and so the list. Unchanged here; brief #1539's intake covers
  button merges.
- Q-1548-8: priority? 1.
- Q-1548-10 (new, this writer's, from the answer to Q-1548-5): how a run knows that no CI proof job runs on the pull
  request. The reading: the one open local-mode record issue, or no `.github/workflows/proof.yml` in the repository;
  build (k)'s brief may settle another reading.
- Q-1548-9 (new, this writer's): the brief names its builds (a) to (c); SPEC-0055 rule 15 already uses (a) to (j), so
  this proposal letters them (k) to (m) and keeps the brief's letters beside them. The reading: the maintainers may keep
  either; the build briefs cite both.

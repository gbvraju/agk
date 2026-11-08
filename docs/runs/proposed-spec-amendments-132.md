# Proposed spec amendments 132 (SPEC-0039; REQ-046)

Date: 2026-11-06 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0320 (brief #667), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The number 132 is the one
reserved for brief #667 in the brief. This amendment is applied to the spec text in the same pull request. It needs a
person's `Approve: SPEC-0039` on the pull request; no session posts it.

1. **The pre-merge tests (rule 6).** After governance passes on the would-be merge, the command runs the test files of
   `[testing] pre_merge_tests` (agk.toml on the default branch) in the same detached worktree. The run uses the heavy lock
   and `env -i` with `PATH`, `HOME`, `AGK_KIT_TESTS=1` and `PYTHONDONTWRITEBYTECODE=1` only, then
   `<python> -m pytest -q --rootdir <worktree> <the files>`, with the configuration file pytest finds above the files.
   Any exit other than 0 holds with `held: the merge with the default branch fails pre-merge tests (<file>::<test>)`,
   exit 3, naming the first failing test (or `heavy lock` or `pytest` when none is named), and nothing is merged,
   recorded or filed.
2. **The setting (rule 6).** `pre_merge_tests` is a non-empty list of file paths inside the repository, with no globs.
   Without the key, none runs. This repository's `agk.toml` lists `tests/kit/test_rule_budget.py`,
   `tests/kit_dev/test_intelligent_testing.py` and `tests/kit_dev/test_kit_manifest.py`. A malformed value is refused
   before anything runs, and a listed name that is not a file of the merge holds; both name `testing.pre_merge_tests`.
3. **Tests.** The Tests line of rules 6 and 7 gains the cases of brief #667 answer 4: a branch and a default branch that
   are each green and whose merge fails a budget test are held, and the green case merges.

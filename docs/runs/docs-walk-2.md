# Docs walk 2: `docs/guides/existing-codebase.md` (launch docs L2)

Date: 2026-10-19 (from `date -u`). Run by the implementation session on a throwaway copy of a small repository (a Python package of 12 lines with one test, a `Makefile` with a
`test` target and a `pyproject.toml`, a README that documents two behaviours), with a local bare repository as `origin` (no GitHub writes, no network). The kit's scripts were called
from this checkout in place of the plugin's slash commands (the skills run the same scripts). Kit 0.25.0. Nothing was written to this repository by the walk.

## What was walked, and what was not

| Guide step | Walked | How |
| --- | --- | --- |
| 1 `/agk:adopt` | yes | `adopt.py . --dry-run`, then `adopt.py .`; `git status` before and after |
| 1 reviewers, commit | yes | `reviewers.py --codeowners --write`, `make -f agk.mk agk-governance` |
| 2 baseline requirement | yes | `intake.py ids`, `stub`, the requirement, a Draft spec, `intake.py check`, governance |
| 3 baseline tests | yes | two tests with `REQ-004 AC1` and `AC2` markers, the requirement set `done`, `Behaviour: unchanged` |
| 4 `project_tests` | yes | the edit without and with an ADR; `proof.py` with the setting empty |
| 5 first real change | partly | a failing test first and the change; `proof.py --base origin/main`; no architect session, no pull request |

## The record

```
$ python3 scripts/agk/adopt.py . --dry-run          (before `git remote set-head`)
refused: cannot tell the default branch (path class .git/refs/remotes/origin/HEAD); run `git remote set-head origin --auto` in TARGET, or check out the default branch of a repository without an origin remote, then run adopt again
$ git remote set-head origin --auto
origin/HEAD set to main
$ python3 scripts/agk/adopt.py . --dry-run
...                                                   (a list of `create` lines; no line for the Makefile, pyproject.toml, tests/test_wc.py or the README)
dry run: 605 files would change; nothing was written
$ python3 scripts/agk/adopt.py .                       (`git status` afterwards: only untracked paths; no tracked file modified)
$ make governance
make: *** No rule to make target 'governance'.  Stop.
$ make -f agk.mk agk-governance                        (nine lines starting `ok`; exit 0)
$ python3 scripts/agk/reviewers.py --codeowners --write
wrote agk block of .github/CODEOWNERS

$ python3 scripts/agk/intake.py ids --sentence "Running wc on a text file prints the number of words in it, where words are separated by any white space."
{"req": "REQ-004", "spec": "0001", "adr": "0002", "slug": "running-wc-on-a-text-file-prints-the-number-of-words-in-it-w"}
$ python3 scripts/agk/intake.py check --base origin/main
ok intake

(agk.toml: project_tests changed from "" to "python3 -m pytest -q", no ADR)
$ make -f agk.mk agk-governance
FAIL protected-changes: protected path class 'agk.toml' changed without an ADR that names it (added or modified, not a Status-only edit)
(a Proposed ADR with `Protected classes: agk.toml` added)
$ make -f agk.mk agk-governance                        (nine `ok` lines)

(every `Status: planned` in docs/requirements.md set to `done` by one sed command, the kit's REQ-001 to REQ-003 included)
$ make -f agk.mk agk-governance
FAIL requirements: REQ-001: done requires a test marker under the test directories
FAIL requirements: REQ-002: done requires a test marker under the test directories
FAIL requirements: REQ-003: done requires a test marker under the test directories
(REQ-001 to REQ-003 set back to planned; REQ-004 `done`)
$ make -f agk.mk agk-governance                        (nine `ok` lines)

$ python3 scripts/agk/proof.py --base origin/main --body body-baseline.md --json      (body: Behaviour: unchanged)
{"outcome": "skipped", "reason": null, "test_files": ["tests/test_wc_baseline.py"], ...}

(a test `test_a_missing_file_exits_with_one` added, failing on the old code; wc changed to print an error and return 1)
$ python3 scripts/agk/proof.py --base origin/main --body body-change.md --json
{"outcome": "proven", "reason": null, "test_files": ["tests/test_wc_baseline.py"], ...}
(project_tests set to "")
$ python3 scripts/agk/proof.py --base origin/main --body body-change.md --json
{"outcome": "unknown", "reason": "no-project-tests", "test_files": ["tests/test_wc_baseline.py"], ...}
```

`python3 -m pytest -q` in the adopted copy: `3 passed in 118.23s (0:01:58)` the first time and `3 passed in 11.33s` on a second and a third run, for three tests of the
project's own (the kit's 600 files sit under `tests/`). The cause was not found (`Q-K4-199`).

## Findings, and what was done about each

Each is a place where the guide was wrong or silent when set against the walk. All are fixed in `docs/guides/existing-codebase.md` before this pull request was pushed.

| # | Where | Finding | Fix |
| --- | --- | --- | --- |
| 1 | step 1 | adopt refuses when `origin/HEAD` is unknown (a repository made with `git init` and `git remote add`); the message names the fix, the guide did not | step 1 says it and gives `git remote set-head origin --auto` |
| 2 | step 1 | `make governance` does not exist in an adopted repository (the `Makefile` is the project's); the guide, written from the new-repository path, used it | the kit's checks are `make -f agk.mk agk-governance` throughout; the difference is stated |
| 3 | step 4 | `project_tests` is empty after adopt, so the `proof` check reads `unknown` (`no-project-tests`); the guide did not say | new step 4 |
| 4 | step 4 | editing `agk.toml` needs an ADR naming `agk.toml`; the failure text is quoted | step 4 quotes the message |
| 5 | step 3 | setting every requirement `done` also sets the kit's REQ-001 to REQ-003 and governance fails; a reader doing the same would meet it | step 3 says to leave REQ-001 to REQ-003 alone |
| 6 | step 4 | the test command runs twice within `proof_timeout`; the guide did not say what a slow suite reads | step 4 says `unknown` |

## Not covered

No pull request was opened, no GitHub write was made and no architect or implementation session was started. The pilot's two proven examples (the brief asks to link them by their
records in this repository) are not recorded in this repository, so none is linked (`Q-K4-197`). No outside developer has followed the guide.

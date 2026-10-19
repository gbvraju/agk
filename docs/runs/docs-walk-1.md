# Docs walk 1: `docs/guides/getting-started.md` (launch docs L1)

Date: 2026-10-19 (from `date -u`). Run by the implementation session on a throwaway directory, with a local bare repository as `origin`
(no GitHub writes, no network) and the kit's scripts called from this checkout in place of the plugin's slash commands (the skills run the same scripts, `skills/*/SKILL.md`). Kit
0.25.0. Nothing was written to this repository by the walk. The walk was run twice: the first time to learn the path, the second time (step 1 to step 4) typing the commands of the
guide as written.

## What was walked, and what was not

| Guide step | Walked | How |
| --- | --- | --- |
| Before you start | no | tools of the reader's machine |
| 1 empty repository, first commit | yes | `git clone` of an empty bare repository, `git branch -M main`, `git commit`, `git push -u origin main` |
| 2 install the plugin | no | writes the reader's user settings; recorded for kit 0.10.0 in `docs/runs/plugin-live-proof.md` |
| 3 `/agk:init` | yes | `init.py . --dry-run`, then `init.py .` |
| 4 reviewers, `make governance`, commit, push | yes | |
| 5 `/agk:ruleset` | no | needs a GitHub login with admin; the plan reads only (`docs/runs/ruleset-sandbox-proof.md`) |
| 6 `/agk:start` | yes | `playbook.py start-ids`, two files, `check-start`, `make governance`, `next-steps` |
| 7 `/agk:spec` | yes | `intake.py ids`, `stub`, the requirement and the Draft spec, `check`, `make governance`, `next-steps` |
| 8 architect | partly | `playbook.py architect` only; no session was started |
| 9 to 12 | no | a pull request, a verdict comment, a merge and a Monday run need GitHub |

## The record

```
$ git clone origin.git proj
warning: You appear to have cloned an empty repository.
$ git push -u origin main
branch 'main' set up to track 'origin/main'.

$ python3 scripts/agk/init.py . --dry-run
dry run: 607 files would be created; nothing was written
notice: config/reviewers.yaml maps `maintainers` to the placeholder @REPLACE-ME
...
$ python3 scripts/agk/init.py .
installed 607 files

$ python3 scripts/agk/reviewers.py --codeowners --write
wrote .github/CODEOWNERS
$ make governance            (nine lines starting `ok`, the last `ok reviewers (.github/CODEOWNERS matches)`; exit 0)
$ git add -A && git commit -m "Install agk" && git push origin main
```

`make governance` with the placeholder still in place printed the same nine `ok` lines (exit 0): the placeholder is reported by `agk doctor`
(`placeholder-team-reviewers`, `placeholder-team-codeowners`), not by a governance check.

```
$ python3 scripts/agk/playbook.py start-ids --statement "A small tool that counts words in a text file, for people who write documentation."
{"adr": "0002", "slug": "a-small-tool-that-counts-words-in-a-text-file-for-people-who", "branch": "start/a-small-tool-that-counts-words-in-a-text-file-for-people-who"}
$ python3 scripts/agk/playbook.py check-start        (first try)
FAIL playbook: rule 5: the Decision lacks the numbered items Milestones, Non-goals, Done means
$ python3 scripts/agk/playbook.py check-start        (after giving Non-goals and Done means list lines)
ok playbook-start
$ python3 scripts/agk/playbook.py next-steps         (commit message, push command, pull request body; ends with the line that says what the checks cannot check)

$ python3 scripts/agk/intake.py ids --sentence "The tool refuses a file that is not text."
{"req": "REQ-004", "spec": "0001", "adr": "0003", "slug": "the-tool-refuses-a-file-that-is-not-text"}
$ python3 scripts/agk/intake.py check --base origin/main
ok intake
$ python3 scripts/agk/new_spec.py brief "Count words in a file"
created docs/briefs/count-words-in-a-file.md
$ python3 scripts/agk/playbook.py architect
Start the architect role from the repository root with:

    claude --agent architect

agk.toml: present
gh: not logged in or not working
default branch: main
The role file is .claude/agents/architect.md;
its guard is .claude/hooks/architect_guard.py.

$ make test
825 passed, 2 skipped in 149.72s (0:02:29)
no tests ran in 0.01s        (the project's own tests: none yet; exit 0)
```

## Findings, and what was done about each

Findings 1 to 8 are places where the first draft of the guide was wrong, unclear or silent when set against the walk and the files it
quotes. Each is fixed in `docs/guides/getting-started.md` before this pull request was pushed.

| # | Where | Finding | Fix |
| --- | --- | --- | --- |
| 1 | step 4 | the draft said a check fails on `@REPLACE-ME`; the walk shows `make governance` passes, only `agk doctor` reports it | the troubleshooting line names the two doctor findings and says `make governance` does not fail |
| 2 | step 5 | the draft said phase 1 comes first; after step 4's push `governance` has run on `main`, so the plan picks phase 2 | step 5 says the phase is chosen for you and when each is chosen; step 11 and the README follow |
| 3 | step 8 | the draft let the architect approve the spec; `check_specs.py` rule 23 fails an implementation pull request unless an Approved spec names the requirement, and the architect never sets `Approved` unless a person orders it | step 8 says the spec must be Approved before step 9, gives the failure text, says rule 24 (no open question) and who changes the line |
| 4 | step 9 | the draft quoted a job summary for the proof outcome; the outcome is in the names of the job's steps (`outcome: proven`, `outcome: not-proven (reason)`) | step 9 and the troubleshooting line quote the step names |
| 5 | step 4 | nothing told the reader that `docs/adr/0001-adopt-agk.md` stays `Proposed`; the drift audit lists a Proposed ADR older than 14 days | step 4 says to set it `Accepted` in its own pull request after step 6 |
| 6 | step 2 | the draft said Claude Code asks to trust the folder; no proof shows it for a user-scope plugin | the sentence is removed |
| 7 | `make test` | `make test` in a new repository runs 825 tests and took 2 minutes 29 seconds | the troubleshooting section says to expect two to three minutes |
| 8 | step 1 | `git clone` of an empty repository prints a warning | step 1 says the warning is expected |
| 9 | `playbook.py check-start` | the message `the Decision lacks the numbered items` is also printed when the three items exist but have no list lines under them (the first try above); a reader cannot tell what is missing | not fixed here (a script change): `Q-K4-191`, ruled a residual (due 2026-11-15) |

## Not covered

No outside developer has followed the guide. Steps 5, 8 and 9 to 12 and the plugin install have not been walked by anyone for this kit version; the guide marks the ruleset apply
and the architect step **(not yet proven live)**. The "10 minutes" of the README is not a measurement `(verify)`.

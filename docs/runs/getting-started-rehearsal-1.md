# Getting-started rehearsal 1: `docs/guides/getting-started.md` on a fresh local repository (stable release item 5)

Date: 2026-10-24 (from `date -u`). Run by the implementation session, from the brief in issue #138, in a new empty directory outside this repository, with its own `HOME` (so the plugin settings of the session were not touched)
and a local bare repository as the stand-in for `origin`. No GitHub repository was created, nothing was pushed to GitHub and no account was used. The guide read is the one at tag `v0.51.0`, the latest tag (the tag of kit
0.52.0 does not exist yet); the plugin the guide's step 2 installs is the one on `main`, kit **0.52.0** (commit `efc8aa9`), so the walk ran on 0.52.0. The guide was followed in order and no knowledge the guide does not give
was used, except where a row says so. Nothing in the guide was fixed: each `unclear` and `failed` row has a proposed fix at the end, for the maintainers to decide.

Statuses: `worked`; `unclear` (what I had to guess); `failed` (the output); `not run: needs a hosted repository`; and `not run: needs an interactive Claude Code session`, which the brief does not list: a slash command or a
second `claude` session cannot be typed by the session that ran this rehearsal, and I did not start another model session from inside it.

## Standing facts of the rehearsal

- Slash commands (`/agk:init`, `/agk:start`, `/agk:spec`, `/agk:doctor`) could not be typed. Each was run the way the plugin's own `skills/<name>/SKILL.md` says (the same scripts from the installed plugin, with `CLAUDE_PLUGIN_ROOT` set to
  the installed plugin), and the steps that are model work (the vision, the charter, the requirement and the spec) were written by this session following the skill text. Every such row is `unclear` for that reason: a newcomer
  types the slash command; I read the skill file the guide does not mention.
- `origin` was a local bare repository, a stand-in. A pull request and its merge were stood in for by `git push` of the branch and a local `git merge --squash` on `main`, which is not the guide's path.
- Placeholders: the reviewer handle `@rehearsal-user` (no such account is used), the statement and the sentence of the guide's own examples.

## The record

| # | Step as the guide gives it | What happened | Status |
| --- | --- | --- | --- |
| 0.1 | Before you start: `claude --version` | `2.1.310 (Claude Code)` | worked |
| 0.2 | `gh auth status` | `X Failed to log in to github.com using token (GH_TOKEN)`, `The token in GH_TOKEN is invalid.`, exit 1. The guide says to stop and open an "I got stuck" issue; I went on, because this step needs a login and the rehearsal uses no account | failed |
| 0.3 | `git --version` | `git version 2.43.0` | worked |
| 0.4 | `make --version` | `GNU Make 4.3` | worked |
| 0.5 | `python3 --version` | `Python 3.13.16` | worked |
| 0.6 | `python3 -m pip install pytest` | `Requirement already satisfied`, exit 0 | worked |
| 1 | Step 1: make a GitHub repository, `git clone`, `git branch -M main`, README, commit, `git push -u origin main` | A hosted repository was not made. Stand-in: `git init -b main`, the README, `git commit -m "first commit"` (a commit `70b9871`), later `git push -u origin main` to the local bare repository | not run: needs a hosted repository |
| 2.1 | `claude plugin marketplace add gbvraju/agk` | `Successfully added marketplace: agk (declared in user settings)`, exit 0 (the guide's text `Successfully added marketplace: agk` is a substring; the output has a leading mark and a suffix) | worked |
| 2.2 | `claude plugin install agk@agk` | `Successfully installed plugin: agk@agk (scope: user)`, exit 0. The installed version is 0.52.0 from `main` (`installed_plugins.json`), not the latest tag; the guide says the plugin installs from `main` and how a team pins a release, so this is as written | worked |
| 2.3 | "Start Claude Code in the repository folder with `claude`" | An interactive session was not started | not run: needs an interactive Claude Code session |
| 3 | `/agk:init`, preview, say yes | The slash command was not typed. Ran the two commands of `skills/init/SKILL.md`: `init.py . --dry-run` printed 58 `create ...` lines and `dry run: 58 files would be created; nothing was written` (the guide: 53 at kit 0.28.0, "the number changes with the kit version"); `init.py .` printed `installed 58 files` and the notice that `config/reviewers.yaml` maps `maintainers` to `@REPLACE-ME`. Nothing was committed. The guide's line "225 KB at kit 0.28.0" is about 624 KB now (`du -sk`, without `.git`) | unclear |
| 4.1 | Change `@REPLACE-ME` to `@YOUR-NAME` on the line `maintainers: {github_team: "@REPLACE-ME"}` | The line is there, with a trailing comment `# replace with a user handle or @org/team`; `sed` replaced the handle | worked |
| 4.2 | `python3 scripts/agk/reviewers.py --codeowners --write`, then `make governance` | `wrote .github/CODEOWNERS`, then ten lines starting `ok` (the last `ok reviewers (.github/CODEOWNERS matches)`), exit 0, as the guide says. Two differences: one more line that starts neither `ok` nor `skipped`: `specs: no pull request body; the lifecycle rule for Advances is skipped`; and the two `skipped` lines come in the other order (`skipped (no open pull requests file)`, then `skipped (no comments file)`) | unclear |
| 4.3 | `git add -A`, `git commit -m "Install agk"` | Commit `3829313` | worked |
| 4.4 | `git push origin main`; open the Actions tab and see `governance` end green | Not pushed to GitHub | not run: needs a hosted repository |
| 4.5 | After step 6, set `docs/adr/0001-adopt-agk.md` to `Accepted` "in a pull request of its own" | The `Status:` line was changed on a branch, `make governance` printed ten `ok` and exit 0, and the branch was merged locally; no pull request was opened | not run: needs a hosted repository |
| 5 | `/agk:ruleset`, apply, `/agk:ruleset` again | Needs admin on a hosted repository | not run: needs a hosted repository |
| 6.1 | `/agk:start "A small tool that counts the words in a text file, for people who write documentation."` | The slash command was not typed. `git fetch origin main` first failed (`'origin' does not appear to be a git repository`) and `playbook.py start-ids` printed `FAIL playbook: the base has no requirements file (path class docs/)`, exit 1, with no `origin`; with the local bare `origin` it printed the ids (`0002`, branch `start/a-small-tool-that-counts-the-words-in-a-text-file-for-people`). The skill then asks the product owner about six discovery topics (`users`, `existing`, `runs`, `data`, `scale`, `compliance`) and the guide does not say so; nobody was there to answer, so I wrote `not known yet` for all six. I wrote `constitution/vision.md` and `docs/adr/0002-project-charter.md`; `playbook.py check-start` printed `ok playbook-start` and `make governance` printed ten `ok` | unclear |
| 6.2 | Commit with the printed message, push, open the pull request with the printed body, wait for green, merge (squash) | Committed (`start: the vision and the project charter`) and pushed the branch to the local `origin`; the printed body and the next steps were read. The pull request, the green `governance` run and the merge on GitHub were not made (stand-in: a local squash merge) | not run: needs a hosted repository |
| 7.1 | `/agk:spec "The tool refuses a file that is not text."` | The slash command was not typed. `intake.py ids` printed `intake: kit 0.52.0` and then `{"req": "REQ-101", "spec": "0001", "adr": "0003", ...}` (the requirement starts at 101 in a project; the guide says `REQ-NNN`); the ADR stub was rendered by `intake.py stub`; I wrote the requirement (two criteria, one that refuses) and the Draft spec by the skill's list, including `## Proof` and `## Residual`, which `docs/specs/TEMPLATE.md` does not have; `intake.py check` printed `ok intake` and `make governance` ten `ok`. No question was asked: the sentence settled every point, so the spec says "answered no questions" although no person was there | unclear |
| 7.2 | Commit, push, open the pull request, wait for green, merge | As in 6.2 | not run: needs a hosted repository |
| 8 | `claude --agent architect`; ask the architect for a brief; approve the spec | A second interactive session | not run: needs an interactive Claude Code session |
| 9 | A third session builds from the brief | A third interactive session | not run: needs an interactive Claude Code session |
| 10 | The architect reviews with a `Verdict:` comment; merge | A session and a pull request on GitHub | not run: needs an interactive Claude Code session |
| 11 | `/agk:ruleset` phase 2 | Needs the ruleset of step 5 | not run: needs a hosted repository |
| 12 | The first Monday report: Actions, `product-report`, Run workflow | Needs a hosted repository | not run: needs a hosted repository |

## `/agk:doctor` at the end (the brief's item 3)

Run as `skills/doctor/SKILL.md` says: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/doctor.py" --kit-root "${CLAUDE_PLUGIN_ROOT}"` from the repository root. Exit 4 (not every check could be made). The output, verbatim:

```
agk doctor 0.52.0
?? ruleset-missing error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? ruleset-enforcement error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? ruleset-bypass error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? ruleset-target error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? ruleset-deletion error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? ruleset-linear-history error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? ruleset-force-push error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? ruleset-pull-request error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? required-check-governance error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? repo-auto-merge warn cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? repo-delete-branch warn cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
ok placeholder-team-reviewers error config/reviewers.yaml has no placeholder team
ok placeholder-team-codeowners error .github/CODEOWNERS has no placeholder team
FAIL origin-head warn refs/remotes/origin/HEAD is missing
  fix: run `git remote set-head origin <default_branch>` (no network; `-a` asks the remote)
ok drift-workflow-file error .github/workflows/drift-audit.yml has a schedule
?? drift-workflow-state error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
?? issues-disabled error cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
ok kit-version warn the kit version equals version in agk.toml
ok vendored-missing error every vendored file is present
ok vendored-differs error every vendored file equals the kit's copy
?? default-branch-config warn cannot check (not-github)
  to check: pass --repo OWNER/REPO for a repository on github.com
ok pr-mode warn pr_mode in agk.toml is strict or flow (mode: strict)
summary: 7 ok, 1 fail, 14 cannot-check
```

The 14 `??` lines are the checks that read GitHub; there is no GitHub remote. The one `FAIL`, `origin-head`, is an effect of the local bare `origin` used as a stand-in (its `refs/remotes/origin/HEAD` was never set), not a defect of the guide.

## Counts

26 rows: **worked 9**, **unclear 4**, **failed 1**, **not run: needs a hosted repository 8**, **not run: needs an interactive Claude Code session 4**. The doctor run (item 3) is separate: 7 ok, 1 fail, 14 cannot-check.

## Proposed fixes (for the maintainers to decide; the guide is not changed in this pull request)

1. **Row 0.2, `gh auth status`.** The guide says to stop when what you see differs. A rehearsal or an offline reader cannot pass it. Proposed: say which steps need `gh` (5, 11 and the doctor's remote checks) and that steps 3, 4, 6 and 7 do not.
2. **Rows 3, 6.1 and 7.1, slash commands.** The guide says "In Claude Code type `/agk:...`" and describes what you should see, which is right in an interactive session; but a reader who cannot type them (a script, a rehearsal) has no hint
   that each is the script named in `skills/<name>/SKILL.md`. Proposed: one sentence in "Before you start" or in the reference naming the script behind each slash command.
3. **Row 3, the numbers.** "225 KB at kit 0.28.0" and "53 files" are old; the guide already says the number changes. Proposed: drop the figures, or update them (58 files, about 624 KB at 0.52.0).
4. **Row 4.2, the `make governance` description.** Proposed: say "ten lines starting `ok`, two starting `skipped` and one line that starts `specs:` about a pull request body", and do not fix the order of the two `skipped` lines.
5. **Rows 6.1 and 7.1, a local `origin`.** With no `origin`, `git fetch origin` fails and `start-ids` and `intake.py ids` refuse with `the base has no requirements file (path class docs/)`, which does not say that the cause is a missing `origin/main`. Proposed: say in the message that `origin/<default branch>` could not be read, and in the guide that steps 6 and 7 need `origin`.
6. **Row 6.1, the discovery questions.** `/agk:start` asks up to three questions a round about six topics before it writes the charter; the guide says only "Give it the problem in your own words". Proposed: one sentence in step 6 saying it asks about users, existing systems, where it runs, data, scale and compliance, and that `not known yet` is a valid answer.
7. **Row 7.1, the spec shape.** `skills/spec/SKILL.md` asks for `## Proof` and `## Residual`, which `docs/specs/TEMPLATE.md` does not have, and the guide says the three files are written for you. Proposed: add the two sections to the template or drop them from the skill (the check accepted both shapes only for the skill's form in this walk; the template alone was not tried).
8. **Row 7.1, "answered no questions".** With nobody to answer, the spec records "The maintainers answered no questions before it was written" as the skill says. Proposed: the skill says to write that only when a person confirmed the sentence needs none.
9. **Rows 2.2 and the brief.** The brief asks to follow the guide "from the latest tag"; the guide installs from `main`, so a reader at the tag gets a newer kit than the tag. Proposed: the guide shows the pinned form of step 2 as the default for a rehearsal, or the maintainers tag before the rehearsal.
10. **Steps 8 to 10.** They need two more interactive sessions and GitHub; they were not run. They remain unproven by this rehearsal, as the guide's own **(not yet proven live)** says for 5 and 8.

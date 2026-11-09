# Auto-merge: the guarded merge for the owner

This page is for the owner of a project. It says what the guarded merge setting does and does not do, how to set it up, how
the conductor runs the command, what each line it prints means and how to stop it. It describes `scripts/agk/merge_cleared.py`
as it is on the default branch and the Approved text of SPEC-0039 (rule 11); it decides nothing new.

## What the setting does

Two keys in the `[flow]` table of `agk.toml` turn it on:

```toml
[flow]
auto_merge = true
auto_merge_method = "squash"
```

With both, read from the default branch of the remote as last fetched (never from a pull request), the conductor merges a pull
request in the same act as clearing it: it posts `Verdict: cleared <sha>` and then runs one command, once. The command checks
again, at the moment it runs, everything a person would check before merging:

- the setting, and that the kit is not paused (`paused = true` on the default branch);
- that `<sha>` is still the pull request's head, and that the latest comment starting `Verdict:` reads exactly
  `Verdict: cleared <that full sha>` (a newer `Verdict:` by anyone hides it; a fix list, a short sha or more text never merges);
- the evidence for that head: in CI mode every check of `required_checks` ended `success` on it; in local mode the verdict
  carries `Local evidence:` and `Evidence check: agrees` for that head;
- the hold list: a release, a spec approval still missing, a change to `constitution/`, `config/reviewers.yaml`, the ruleset files
  or `.github/workflows/`, the `agk:hold` label, a draft, an unmerged `Depends-on`, a conflict, and a red default branch;
- that the merge of the head with the default branch passes `make governance` (and the `[testing] pre_merge_tests`, if set)
  before anything is merged.

Then it merges by one squash merge pinned to the sha, so a head that moved is refused by GitHub. After the merge it posts one
record line, runs governance on the merged default branch, and, if that is red, opens the red-branch issue, which holds every
later merge until it is closed.

`auto_merge` is off by default and when absent; `auto_merge_method` accepts only `"squash"`, and any other value merges nothing. It means the same in every `pr_mode`, every `review_mode` and in local mode.
`python3 scripts/agk/doctor.py` prints `auto-merge: off` or `auto-merge: on, method squash`.

## What it does not do

- It does not merge on its own. Nothing runs on a timer; there is no loop. A merge that could not run (the checks still
  pending, the kit paused, GitHub unreachable, the machine asleep) waits for the conductor's next review pass, where
  `session.py review-queue` lists it as `cleared, not merged` and the conductor runs the command again.
- It does not trust a comment. A `Verdict:` comment alone merges nothing; trust rests on who can run the command.
- It never merges anything on the hold list: those wait for you, as before.
- It never tags, approves a review, posts a verdict, changes a workflow or the ruleset, edits or commits a file, pushes or
  reverts, and never runs anything from a pull request's head except governance on its merge with the default branch.
- It never reads a secret: `gh` holds the login.
- A builder never runs it. Only the conductor does (principle 2, session rule 2).

## Accounts: one by default, a second if you want

One account is the default: yours. The conductor, the builders and you all post under it, so nothing else is needed for a merge.
The cost is that GitHub cannot tell who posted a comment; only the conductor's guard and the builders' rules keep the command
in the conductor's hands (the residual of SPEC-0039).

A second account narrows that to one login:

1. Create a second GitHub user for the conductor, give it write access to the repository and no admin. Not a GitHub App: an
   App needs hosting.
2. Sign the conductor's machine in to `gh` with that account, and keep it out of every builder session.
3. List it in `config/reviewers.yaml` (an invented login here):

   ```yaml
   conductor_accounts: [conductor-bot]   # the conductor's own login, e.g. conductor-bot@example.com
   ```

   Sessions act only on verdicts by `verdict_authors` (session rule 1), so list the login there too. The command then also
   requires the verdict's author to be listed, and refuses, naming the setting, a list that holds the placeholder `@REPLACE-ME`
   or an account that is also in `spec_approvers`.

`config/reviewers.yaml` is protected and on the hold list, so this change lands with its own ADR and you merge it yourself.

## Open the record issue

Every merge is recorded by one comment, `Auto merge: #<n> <merge sha> <UTC time> <verdict link>`, on the open local-mode
record issue while local mode is on, otherwise on the one open issue labelled `agk-auto-merge`. With neither open, the command
merges nothing (`held: no record issue (rule 7)`). Open it once:

```sh
gh api repos/{owner}/{repo}/labels -f name=agk-auto-merge -f color=ededed
gh api repos/{owner}/{repo}/issues -f title="Auto merge record" -f "labels[]=agk-auto-merge" \
  -f body="One comment per guarded merge: Auto merge: #<n> <merge sha> <UTC time> <verdict link>."
```

Keep exactly one such issue open; with two, nothing merges.

## Run the command

The conductor runs exactly this, with the pull request number and the full 40-character lower-case head sha, from the project's
own checkout of the default branch. On POSIX:

```sh
python3 scripts/agk/merge_cleared.py --pr <n> --sha <sha>
```

On Windows, in PowerShell, where `python3` is not on the path:

```powershell
python scripts/agk/merge_cleared.py --pr <n> --sha <sha>
```

and in cmd:

```bat
python scripts/agk/merge_cleared.py --pr <n> --sha <sha>
```

The command passes every argument to `gh` as a list, with no shell and no `--jq` filter, so no quoting of PowerShell, cmd or a
POSIX shell can change what it reads. The conductor's guard allows only this form, two options in this order, and only with
`auto_merge = true` both in the checkout and on the default branch. The project settings allow the `python3` form without a
prompt; the `python` form still asks (verify), so an unattended conductor on Windows needs `python3` on its path.

## What each line means

The command prints one line and ends:

- `merge-cleared #<n> <sha12>: merged <merge sha12>` (exit 0): merged, recorded, and governance after the merge was green.
- `merge-cleared #<n> <sha12>: held: <reason>` (exit 3): nothing merged; the reason names a rule or a setting, never a value.
  Some holds clear by themselves (`checks pending`, `paused`, `the default branch is red`) and the next review pass tries
  again. A hold for the hold list (`release`, `spec approval`, `protected class <class>`, `hold label`, `draft`, `depends-on`,
  `conflict`) waits for you. `held: the merge with the default branch fails governance (<step>)` means the head is green alone
  but not on today's default branch: the builder merges the default branch in and pushes again.
- `merge-cleared #<n> <sha12>: refused: <reason>` (exit 1, or 3 for `head moved`): the command will not merge this as asked, for
  example the setting is off or `conductor_accounts` is malformed. `head moved` means `<sha>` is no longer the head: the
  new head needs its own verdict. Exit 4 means GitHub could not
  answer one read five times in a row; a failed read is never taken as a pass.
- `merge-cleared: stopped: default branch red after #<n>` (exit 1): the merge happened, but governance on the merged default
  branch is red. The command opened or updated the issue `The default branch is red` and merges nothing more until it is closed.
  It never reverts: the red-branch fix (a pull request whose first line is `Brief: #<that issue>`) still merges, and closes it.

## Stop merging

- **For good:** set `auto_merge = false` in `agk.toml` by a pull request with an ADR (the file is protected), the same way it was
  turned on. Builds go back to a person merging each cleared pull request.
- **For now:** set `paused = true` at the top of `agk.toml` (also by an ADR, ADR-0196). Every session stops and the command
  holds with `paused`; removing the line resumes everything.
- **One pull request:** add the label `agk:hold`.

A red default branch stops merging by itself until the red-branch issue is closed.

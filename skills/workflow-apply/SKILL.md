---
name: workflow-apply
description: Apply a builder's proposed workflow file to its pull request's branch. Checks each file under .agk/workflow-proposals/, shows the diff, and after the owner's yes moves it into .github/workflows/, commits, pushes to the branch and answers the builder's question. Run by the owner, with the owner's own git and gh.
disable-model-invocation: true
argument-hint: "<pull request number>"
---

# /agk:workflow-apply

A session never changes a workflow file, and the cloud refuses a push that touches `.github/workflows/`. So when a
brief needs a workflow change, the builder commits the whole proposed file at `.agk/workflow-proposals/<name>.yml` on
its branch and posts `Question: Q-<N>-n for the maintainers:` naming `/agk:workflow-apply <pr>` (ADR-0505). This command
is the owner's answer: no copy and paste. It runs on the owner's machine (Windows, macOS or Linux) from the repository's
checkout, with the owner's own `git` and `gh`; the push uses the owner's credentials.

1. **The dry run.** Run, with the pull request number the person gave:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/workflow_apply.py" --pr <n>
```

   It fetches the pull request's head branch into a temporary worktree (removed when it ends) and prints each
   proposal with its target (`.agk/workflow-proposals/<name>.yml -> .github/workflows/<name>.yml`), the diff against
   the branch's current workflow, and the Q id it will answer. It changes nothing. A line starting `refused:` says
   why it stops: the pull request is not open or comes from a fork, its head is the default branch, the branch moved
   since it was read, there is no proposal, a proposal does not parse or names no `jobs`, or (personal mode) there
   are no pull requests, or a proposal is not a regular file or its target path holds a symbolic link. Its last lines
   are `head: <sha>` and the exact `--yes --head <sha>` command for that head. Show the person the diff and every
   `refused:` or `note:` line in plain words.

2. **Ask.** Ask the person whether to apply exactly this diff to the branch. Stop on anything but a clear yes.

3. **Apply.** After the yes, run the same command with `--yes` and the head the dry run printed, copied whole:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/workflow_apply.py" --pr <n> --yes --head <sha>
```

   It refuses, changing nothing, when the branch moved since that dry run: then run the dry run again and ask again.

   It moves each proposal into place, deletes the proposals folder, commits
   `workflow: apply the proposal of #<n> (<Q id>)` on the pull request's branch, checks the committed files byte for
   byte, pushes to that branch only (never a force-push, never the default branch) and posts one comment
   `Answer: <Q id> done: <commit> applied by /agk:workflow-apply`. It needs the newest `Question:` comment whose first
   line says `for the maintainers` and that names this command; without one it changes nothing.

4. **When it cannot finish.** Tell the person what the last lines say and do nothing else. A push refused for lack
   of the workflow permission prints `gh auth refresh -s workflow`: the person runs it and then this command again.
   When the comment could not be posted, the script prints the exact line for the person to post. Never run a fix
   for the person, never push or commit by any other route, and never merge: a governance check fails while a file
   under `.agk/workflow-proposals/` is still on the head, so the pull request waits for this command.

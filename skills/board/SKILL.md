---
name: board
description: Make the plan's GitHub Project board once and keep it in step - create it, link the repository, add the Size and Expected hours fields, and add every open brief issue with its size and hours. Only adds, never removes or edits an item already on the board. Run by the owner, with the owner's own gh.
disable-model-invocation: true
argument-hint: "[--title TEXT] [--owner LOGIN] [--project N] [--yes]"
---

# /agk:board

After `plan_intake.py publish` has made the plan's milestones and brief issues, this command makes the plan's GitHub
Project board and adds every brief to it, so the board is never built by hand (ADR-0506). GitHub Projects are reachable
only through GraphQL, which cloud sessions refuse, so it runs on the owner's machine (Windows, macOS or Linux) from the
repository root, with the owner's own `gh` and its `project` scope.

1. **The dry run.** Run, with the options the person gave:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/board.py" [--title TEXT] [--owner LOGIN] [--project N]
```

   It prints each step it would take: `would create project '<repository> plan' under <owner>` when no board exists
   yet (`--project N`, else `[plan] board` of `agk.toml`), `would link the project to <repository>`, the two fields
   (`Size`, a single select of S, M and L, and `Expected hours`, a number), and one `would add #<n> Size M, Expected
   hours 8` line for each open `agk-brief` issue not yet on the board. It changes nothing. Show the person the lines.

2. **Ask.** Ask the person whether to make exactly these changes. Stop on anything but a clear yes.

3. **Apply.** After the yes, run the same command with `--yes`:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/board.py" [--title TEXT] [--owner LOGIN] [--project N] --yes
```

   It prints `added #<n>`, `set #<n> Size M` and `set #<n> Expected hours 8` lines and ends
   `ok board: <a> added, <b> already there`. On the first run it also prints
   `add to agk.toml under [plan], and commit: board = <n>`: tell the person to add that line and commit it; the command
   never edits the file. Hours are the high end of the brief's `Expected:` range; Milestone and Status are GitHub's own
   fields. An item already on the board is never changed, and nothing is removed.

4. **When it cannot finish.** Tell the person what the last line says and do nothing else. A missing `project` scope
   prints `gh auth refresh -s project` (exit 2): the person runs it and then this command again. Any other failure
   prints `failed: <the command>` (exit 1); running the command again with the printed board number finishes the rest.
   In a cloud session it prints `board: needs a machine with your own gh (cloud sessions cannot reach GitHub Projects)`
   and exits 0. In personal mode there are no GitHub issues, and it says so.

---
name: board
description: Make the plan's GitHub Project board once and keep it in step - copy it from the owner's template board (or create it), link the repository, add the Size, Expected hours, Persona, Requirement, Screens and Sign-off fields, and add every open brief issue with them filled. Only adds, never removes or edits an item already on the board. Run by the owner, with the owner's own gh.
disable-model-invocation: true
argument-hint: "[--title TEXT] [--owner LOGIN] [--project N] [--template OWNER/NUMBER] [--yes]"
---

# /agk:board

After `plan_intake.py publish` has made the plan's milestones and brief issues, this command makes the plan's GitHub
Project board and adds every brief to it, so the board is never built by hand (ADR-0506), copied from the owner's
template board so business can read each card and sign it off (ADR-0507). GitHub Projects are reachable
only through GraphQL, which cloud sessions refuse, so it runs on the owner's machine (Windows, macOS or Linux) from the
repository root, with the owner's own `gh` and its `project` scope.

1. **The dry run.** Run, with the options the person gave:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/board.py" [--title TEXT] [--owner LOGIN] [--project N] [--template OWNER/NUMBER]
```

   It prints each step it would take: `would create project '<repository> plan' under <owner>` when no board exists
   yet (`--project N`, else `[plan] board` of `agk.toml`), or `would copy project <owner>/<number> as '<title>' under
   <owner>` with a template (`--template OWNER/NUMBER`, else `[plan] board_template`), `would link the project to
   <repository>`, each missing field (`Size`, a single select of S, M and L; `Expected hours`, a number; `Persona`,
   `Requirement` and `Screens`, text; `Sign-off`, a single select of Pending, Signed off and Changes asked), and one
   `would add #<n> Size M, Expected hours 8, Persona P1 ..., Requirement REQ-..., Sign-off Pending` line for each open
   `agk-brief` issue not yet on the board. Without a template it also prints the three views to make once in GitHub
   (Sign-off, a board by Status; Questions, a table filtered to `Card kind` Question; Roadmap, by Milestone). Once an
   open `agk-business-question` issue is there it also adds `Card kind`, a single select of Work and Question that
   marks each card (GitHub's own `Type` field is never created or written; an older board's own `Type` field of Work
   and Question is kept). It changes nothing. Show the person the lines.

2. **Ask.** Ask the person whether to make exactly these changes. Stop on anything but a clear yes.

3. **Apply.** After the yes, run the same command with `--yes`:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/board.py" [--title TEXT] [--owner LOGIN] [--project N] [--template OWNER/NUMBER] --yes
```

   It prints `added #<n>`, `set #<n> Size M` and `set #<n> Expected hours 8` lines and ends
   `ok board: <a> added, <b> already there`. On the first run it also prints
   `add to agk.toml under [plan], and commit: board = <n>`: tell the person to add that line and commit it; the command
   never edits the file. Hours are the high end of the brief's `Expected:` range; Persona, Requirement and Screens come
   from the issue's `Persona:`, `Advances:` and `Screens:` lines and Sign-off starts at Pending; Milestone and Status
   are GitHub's own fields. An item already on the board is never changed (a field this run added to the board is filled
   on it once, and a value a person set is never overwritten), and nothing is removed. Business signs off by setting a
   card's Sign-off; the plan's formal gate stays the owner's `Approve: plan` line.

4. **When it cannot finish.** Tell the person what the last line says and do nothing else. A missing `project` scope
   prints `gh auth refresh -s project` (exit 2): the person runs it and then this command again. Any other failure
   prints `failed: <the command>` (exit 1), and a field it could not add also prints
   `board: the field <name> was not added; gh said: <gh's message>`; running the command again with the printed board
   number finishes the rest.
   In a cloud session it prints `board: needs a machine with your own gh (cloud sessions cannot reach GitHub Projects)`
   and exits 0. In personal mode there are no GitHub issues, and it says so.

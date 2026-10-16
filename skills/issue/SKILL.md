---
name: issue
description: Render a GitHub issue from the repository's issue templates and file it after asking. The one command that writes outside the working tree.
disable-model-invocation: true
argument-hint: "proposal|question|report TITLE"
---

# /agk:issue

File one GitHub issue from a template in `.github/ISSUE_TEMPLATE/`. An issue is intake only: it proposes, asks or
reports, and decides nothing.

1. Read the template the user names (`proposal`, `question` or `report`) and fill it from what the user tells you. Link
   the REQ and spec ids the user gave; leave their status alone.
2. Write the rendered body to a file in the system temporary directory and show the title and body to the user.
3. Ask the user whether to file it. Only on a yes, run the user's own `gh`:

   ```
   gh issue create --title "TITLE" --body-file FILE
   ```

Create one issue and stop. Do nothing else on GitHub. Never write into the working tree.

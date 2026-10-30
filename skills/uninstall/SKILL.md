---
name: uninstall
description: Pause the agk kit, or remove it in one reviewable branch (agk uninstall). A dry run by default; never commits, pushes or changes GitHub settings.
disable-model-invocation: true
argument-hint: "[--pause] [--remove-docs] (target directory, default .)"
---

# /agk:uninstall

Pause the kit first, or remove it. Both are a dry run until the person agrees; `--write` then makes one new branch in
the repository and writes the change there, uncommitted. The removal deletes only the kit files that still match a
released copy, lists every kit file the project changed, keeps the project's own work (requirements, ADRs, specs,
briefs, the vision, design documents, the tests) and prints, never does, what to undo on GitHub.

1. To pause (no check blocks, no session acts, nothing is deleted), preview:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/uninstall.py" . --pause
   ```

   Show the output. Only after the person agrees, build the branch:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/uninstall.py" . --pause --write
   ```

2. To remove, preview (add `--remove-docs` when the person asks which of the project's own documents they could delete
   by hand; the tool never deletes them):

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/uninstall.py" .
   ```

   Show the output: the files to delete, the files to edit, every `changed` kit file (kept for the person to decide)
   and the GitHub list. Only after the person agrees, build the branch:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/uninstall.py" . --write
   ```

3. Show the printed protected classes and the ADR skeleton. Write no ADR and edit no protected path yourself: the
   pull request needs an ADR that the maintainers decide. The person commits the branch, pushes it and opens one pull
   request, which git can revert.
4. Show the GitHub list (the ruleset by name, the labels, the issues, the plugin removal command). Each is a person's
   act with admin rights; do none of them.

Do not commit, push or merge. Do not delete a file the output lists as `changed` or `remove by hand`.

---
name: init
description: Install the agk kit into an empty repository (agk init). Writes new files only; never commits or pushes.
disable-model-invocation: true
argument-hint: "[target directory, default .]"
---

# /agk:init

Install the kit into an empty repository. Run the script of the same name from the plugin root; it refuses rather than
overwrite, and writes nothing when any file conflicts.

1. Preview, with the target directory (the current directory when none is given):

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/init.py" . --dry-run
   ```

2. Show the output to the user. Run it again without `--dry-run` only after the user agrees:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/init.py" .
   ```

3. Show the printed branch rules, scanner exclusions and plugin settings entries as they are. Do not apply any of them.

Do not commit, push or merge. Do not set a spec `Approved` or an ADR `Accepted`. Stop after reporting what was created.

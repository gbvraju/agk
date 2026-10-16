---
name: adopt
description: Install the kit into an existing repository without touching product files (agk adopt). Never commits or pushes.
disable-model-invocation: true
argument-hint: "[target directory, default .]"
---

# /agk:adopt

Install the kit into an existing repository. The script touches no product file: it writes the files the kit owns and
marked blocks, and refuses before any write when something conflicts.

1. Preview:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/adopt.py" . --dry-run
   ```

2. Show the output to the user. Run it again without `--dry-run` only after the user agrees:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/adopt.py" .
   ```

3. Show the printed branch rules, scanner exclusions and plugin settings entries as they are. Do not apply any of them.

Do not commit, push or merge. Do not set a spec `Approved` or an ADR `Accepted`. Stop after reporting what was written.

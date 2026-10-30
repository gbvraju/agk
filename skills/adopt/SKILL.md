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

   If it refuses because the plugin's kit files are not those of a release, show the message and the printed plugin
   settings entries and stop: the person installs the plugin at that release's tag (the `ref` of the agk marketplace
   entry), then runs `/agk:adopt` again.

2. Show the output to the user. Run it again without `--dry-run` only after the user agrees:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/adopt.py" .
   ```

3. Show the printed branch rules, scanner exclusions and plugin settings entries as they are. Do not apply any of them.

Do not commit, push or merge. Do not set a spec `Approved` or an ADR `Accepted`. Stop after reporting what was written.

---
name: upgrade
description: Bring an agk install from its recorded kit version to this plugin's kit version (agk upgrade). Never commits or pushes.
disable-model-invocation: true
argument-hint: "[target directory, default .]"
---

# /agk:upgrade

Upgrade an init or adopt target from the kit version in its `agk.toml` to this plugin's kit. A file the user edited
stops the whole run and nothing is written; user-owned files are never rewritten.

1. Preview:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/upgrade.py" . --dry-run
   ```

2. Show the output to the user. Run it again without `--dry-run` only after the user agrees:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/upgrade.py" .
   ```

3. Show the printed protected classes, the changed templates and the ADR skeleton. Write no ADR and edit no protected
   path yourself: the upgrade pull request needs an ADR that the maintainers decide.

Do not commit, push or merge. Do not set a spec `Approved` or an ADR `Accepted`.

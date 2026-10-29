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
4. Once the person wrote that ADR (titled from the skeleton, with its `Requirements:` line), print the commit message and
   the pull request body. Add `--brief <n>` when the work answers a brief, or `--brief none` when the person says the
   repository has no open brief. The body is printed as a file path and its text, only after the repository's own
   `check_pr_body.py` passed it; use it unchanged.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/upgrade.py" . --next-steps --brief <n|none>
   ```

Do not commit, push or merge. Do not set a spec `Approved` or an ADR `Accepted`.

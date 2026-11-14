---
name: upgrade
description: Bring an agk install from its recorded kit version to this plugin's kit version (agk upgrade) as one ready pull request: its own branch, the files, the ADR and the checked body. Never commits, pushes or merges.
disable-model-invocation: true
argument-hint: "[target directory, default .]"
---

# /agk:upgrade

Upgrade an init or adopt target from the kit version in its `agk.toml` to this plugin's kit, so that the upgrade
arrives as one ready pull request: the files, the ADR with every section and the body. A file the user edited stops
the whole run and nothing is written; user-owned files are never rewritten.

1. Preview (add `--write-adr` to also see the name of the ADR the upgrade will write):

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/upgrade.py" . --dry-run
   ```

   Show the output to the user. `<version>` below is the kit version its summary line names; `<default branch>` is
   `default_branch` in `agk.toml`, else `main`. When it says `0 files would change` and names no version line, stop: there is nothing to upgrade.

2. Only after the user agrees, create the upgrade branch from the default branch before anything is written:

   ```
   git fetch origin <default branch>
   git switch -c upgrade/agk-<version> origin/<default branch>
   ```

   If the working tree has changes or the branch exists, stop and tell the user; never stash, reset or delete.

3. Write the upgrade and its ADR (`docs/adr/<next>-upgrade-agk-to-<version>.md`: every section `check_adrs.py`
   requires, each protected class the upgrade changed, `Status: Proposed`):

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/upgrade.py" . --write-adr
   ```

   Show the printed lines. Edit no protected path yourself and never set the ADR `Accepted`.

4. Run the local gate in the target and show its result; on a failure stop and show it:

   ```
   make lint
   make governance
   ```

5. Print the commit message and the pull request body. Add `--brief <n>` when the work answers a brief, or
   `--brief none` when the person says the repository has no open brief. The body is printed as a file path and its
   text, only after the repository's own `check_pr_body.py` passed it; use it unchanged.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/upgrade.py" . --next-steps --brief <n|none>
   ```

6. Tell the user the upgrade is held for the owner's merge: it raises `version` in `agk.toml`, which
   `merge_cleared.py` holds as a release (its rule 5), so the person commits, pushes, opens the pull request with that
   body and merges it after review.

Do not commit, push or merge. Do not set a spec `Approved` or an ADR `Accepted`.

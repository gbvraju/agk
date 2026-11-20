---
name: personal-adopt
description: Personal mode only. Read the survey's reading list of the product's code and draft requirements, specs and ADRs, each claim cited to a real line range, into the private sidecar for the person to confirm at their own terminal. Writes nothing in the product clone; never confirms.
disable-model-invocation: true
argument-hint: "[--sidecar DIR]"
---
<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->

# /agk:personal-adopt

Draft the decisions already in the product's code as records in the person's private sidecar (SPEC-0041 rules 13
and 14). Run it from the product clone, which must already be attached (`personal_state.py attach`). Nothing is
written in the clone or under its `.git/`, and nothing rendered is decided until the person confirms it.

1. Survey the clone and tell the person the coverage line it prints (`<n> of <m> files read`):

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/survey.py"
   ```

2. Read only the files of `reading_list` in the sidecar's `cache/inventory.json`, each at the `blob` the inventory
   names for it (`git --no-optional-locks cat-file -p <blob>`). Read no other file and run no product code or tool.

3. Write the proposals as one JSON file at `cache/proposals.json` in the sidecar (its `cache/` is ignored), never in
   the clone:

   ```json
   {"requirements": [{"title": "...", "claims": [{"statement": "...", "citations": ["src/a.py:10-24@<blob>"]}]}],
    "specs": [{"title": "...", "requirements": [0], "claims": [...]}],
    "adrs": [{"title": "...", "specs": [0], "requirements": [0], "claims": [...]}]}
   ```

   Each statement says in plain words what the cited lines show, with one or more citations `path:start-end@blob`
   (the full blob from the inventory, lines counted from 1). Set `"verify": true` on a claim the lines do not fully
   show. Do not copy code into a statement: an excerpt beyond `[personal] quote_lines` (0 by default) is refused.
   Never write a secret, a key, a password or personal data into the file. `requirements` and `specs` name records of
   the same file by their index.

4. Check it and tell the person the number of claims refused (the last line, `<k> of <n> claims refused`). Each
   refused line names the claim's position and the rule; fix or drop those claims and check again:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/personal_adopt.py" check <sidecar>/cache/proposals.json
   ```

5. Only after the person agrees, render. It writes the records with a claim left into the sidecar in one commit
   (requirements `planned`, specs `Draft`, ADRs `Proposed`) and prints the `confirm` command of each:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/personal_adopt.py" render <sidecar>/cache/proposals.json
   ```

6. End by listing the printed `personal.py confirm <id> --sidecar <dir>` commands for the person to run at their own
   terminal. Never run `personal.py confirm` yourself: it is refused in an agent session, and the yes is the
   person's.

Do not commit or push in the product clone. Do not set a spec `Approved`, an ADR `Accepted` or a requirement `done`.

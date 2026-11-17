---
name: setup
description: Read this machine and this project, size the AI workforce from memory and cores, and show the plan and the setup table (agk setup); the status form changes nothing. This first form installs nothing and never commits, pushes or merges.
disable-model-invocation: true
argument-hint: "[status]"
---
<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->

# /agk:setup

Run it from Claude Code in the project's folder (`claude "/agk:setup"`, or typed in a session). Two forms: `/agk:setup`
(read the machine and the project and show the plan) and `/agk:setup status` (show the table again). The work is one
kit helper, `setup.py`, run from this plugin and never installed into the project. It reads everything it can itself
and asks nothing that it can read. This first form (SPEC-0065 build (a)) installs nothing and writes no file: a
missing tool shows as `waiting` with what to install, and the later builds install it on the person's yes.

## /agk:setup status

1. Run the status form and show the table in plain words: each step `done`, `skipped`, `waiting` or `failed`, with its
   note. Change nothing.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" status
   ```

## /agk:setup

1. Run the plan form and show its plan (eight lines or fewer) and the table as printed. Ask the person nothing.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" plan
   ```

2. The builders line names the figure, the limit that applied and why. When the person wants fewer builders, run the
   plan again with `--builders <n>`; a figure above the cap is refused, and you say so in one line.
3. For each `waiting` step, tell the person in one line what its note says. The proof steps are listed as not yet run: the
   plan runs none of them. In `/agk:setup status`, which runs them, name each `failed` proof step and suggest
   `/agk:doctor`.
4. For the steward or a script, the same table is `--json`: `steps` (`step`, `result`, `note`), `pending`, `roles` and
   `builders`.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" plan --json
   ```

Never ask for, store or print a password or a sign-in secret; the command never shows a remote's or a proxy's
credentials.

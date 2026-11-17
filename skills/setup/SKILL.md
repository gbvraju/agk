---
name: setup
description: Read this machine and this project, size the AI workforce from memory and cores, ask at most five plain questions, show the plan and the setup table, and on the person's yes propose the project settings as one change for review (agk setup); the status form changes nothing. It installs nothing and never commits, pushes or merges.
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
and asks nothing that it can read. It installs nothing yet (SPEC-0065 builds (a) and (b)): a missing tool shows as
`waiting` with what to install, and the later builds install it on the person's yes. The only file it writes is the
project-settings change of step 5, on a new branch, after the person's yes.

## /agk:setup status

1. Run the status form and show the table in plain words: each step `done`, `skipped`, `waiting` or `failed`, with its
   note. Change nothing.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" status
   ```

## /agk:setup

1. Read the questions the machine and the project leave open (at most five, often none):

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" ask --json
   ```

   Ask each `text` exactly as given, one at a time, offering its `choices` with its `recommend` first. Say no setting,
   file or command name to the person. Ask nothing else.
2. Run the plan form with the answers, one `--answer <id>=<choice>` each, and show its plan (eight lines or fewer) and
   the table as printed. Its last line, `For the developer:`, names the settings for a developer; for a business user
   say only that the project's settings will be proposed for the owner to review.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" plan --answer where=local --answer team=solo
   ```

3. The builders line names the figure, the limit that applied and why. When the person wants fewer builders, run the
   plan again with `--builders <n>`; a figure above the cap is refused, and you say so in one line.
4. For each `waiting` step, tell the person in one line what its note says. The proof steps are listed as not yet run: the
   plan runs none of them. In `/agk:setup status`, which runs them, name each `failed` proof step and suggest
   `/agk:doctor`.
5. Ask for one yes to the plan. On anything but a yes, stop: nothing changes. On the yes, run the settings form with
   the same answers (and the same `--builders`, if lowered):

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" settings --yes --answer where=local --answer team=solo
   ```

   It writes only the settings the project does not already hold, with the project's ADR, on a new branch, and prints
   the commands that save, check and send the change; show them for the person to run. When it says every setting
   already matches, or the answer was "for me only", there is nothing to send. You never run those commands yourself.
6. For the steward or a script, the same table is `--json`: `steps` (`step`, `result`, `note`), `pending`, `roles` and
   `builders`.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" plan --json
   ```

Never ask for, store or print a password or a sign-in secret; the command never shows a remote's or a proxy's
credentials.

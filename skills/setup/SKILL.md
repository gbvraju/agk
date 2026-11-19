---
name: setup
description: Read this machine and this project, size the AI workforce from memory and cores, ask at most five plain questions, show the plan and the setup table, and on the person's yes propose the project settings as one change for review and, on Windows with WSL 2 chosen, set up the WSL workforce through /agk:wsl's own script (agk setup); the status form changes nothing and shows the team, the restart form restarts only the roles this machine may run, and the back form removes only the scheduler tasks it added and prepares the reverse settings change. It never commits, pushes or merges.
disable-model-invocation: true
argument-hint: "[status|restart|back]"
---
<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->

# /agk:setup

Run it from Claude Code in the project's folder (`claude "/agk:setup"`, or typed in a session). Four forms:
`/agk:setup` (read the machine and the project and show the plan), `/agk:setup status` (show the table and the team
again), `/agk:setup restart` (restart this machine's stopped roles) and
`/agk:setup back` (undo what it added). The work is one kit helper, `setup.py`, run from this plugin and never installed
into the project. It reads everything it can itself
and asks nothing that it can read. A missing tool shows as `waiting` with what to install. On Windows with WSL 2
chosen, step 6 sets the machine up through `/agk:wsl`'s own script and helper, called unchanged, after the person's
yes. The only project file it writes is the project-settings change of step 5, on a new branch, after the yes.

## /agk:setup status

1. Run the status form and show the table in plain words: each step `done`, `skipped`, `waiting` or `failed`, with its
   note. Change nothing.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" status
   ```

2. Show its `Team` lines as printed: who holds the conductor's lease, the live steward, each builder with its brief,
   the members listed, what waits on the owner and this machine's roles. It posts nothing.

## /agk:setup restart

1. When this machine's roles have stopped, show what would restart, changing nothing; it restarts exactly the roles
   the project allows here, so a builders-only machine stays builders-only:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" restart
   ```

2. Ask for one yes. On the yes, run it with `--yes`. It restarts the conductor itself (only on a machine allowed to
   run it); for the builders run `/agk:launch`, which shows its own plan and asks its own yes; for the steward show
   the person the printed command (`claude --agent steward`) to open it in a new terminal, since the steward is their
   own session.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" restart --yes
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

3. The `Roles here` line names this machine's roles and why. When the person wants fewer, run the plan again with
   `--roles <role,role>`; a role the project does not allow here is refused, and you say so in one line. The builders
   line names the figure, the limit that applied and why. When the person wants fewer builders, run the
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
6. On Windows, when the person chose WSL 2 (`windows=wsl`) and the AI work runs on this machine or for them only, run
   the WSL form after the same yes, with the same answers. Podman is the engine unless the person chose Docker
   (`--answer engine=docker`). Show its lines as printed: `/agk:wsl`'s plan, the table and the status lines.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" wsl --yes --answer windows=wsl --answer where=local
   ```

   For each `waiting` step tell the person what its note says: the GitHub and Claude sign-ins are the normal sign-ins
   in the browser, in the `AGK shell (WSL)` tab of Windows Terminal. When a step needs a restart of Windows or a new
   window, or the last line starts `stop:`, say so and stop; the next `/agk:setup` resumes. The `scheduler` row waits
   until the settings change of step 5 (the WSL launch adapter) is merged; then the next `/agk:setup` adds the one
   scheduler task through the same script. For me only, there is no scheduler task.

7. For the steward or a script, the same table is `--json`: `steps` (`step`, `result`, `note`), `pending`, `roles` and
   `builders`.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" plan --json
   ```

## /agk:setup back

1. Show what back would do, changing nothing: the scheduler tasks this command added on this machine, and whether
   there are project settings to reverse.

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" back
   ```

2. Ask for one yes. On anything but a yes, stop: nothing changes. On the yes, run it with `--yes`:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/setup.py" back --yes
   ```

   It removes only the scheduler tasks it recorded, by their names, and prepares the reverse of the settings it
   proposed that the project still holds, with the project's ADR, on a new branch; show the printed commands for the
   person to run. It never uninstalls a tool, never removes a worktree and never deletes data, and you never run those
   commands yourself. A `failed` row names what to run again.

Never ask for, store or print a password or a sign-in secret; the command never shows a remote's or a proxy's
credentials.

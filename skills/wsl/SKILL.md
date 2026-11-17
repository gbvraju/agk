---
name: wsl
description: Move this Windows machine's AI workforce into WSL 2 and back (agk wsl), with the checks, the sign-ins, the launch-adapter pull request and the watchdog prepared for the person. Never commits, pushes or merges.
disable-model-invocation: true
argument-hint: "[status | back]"
---
<!--
SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
SPDX-License-Identifier: LicenseRef-AGK-Proprietary
AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
-->

# /agk:wsl

Run it from Claude Code on the Windows host, in the project's Windows checkout (`claude "/agk:wsl"`, or typed in a
session). Three forms: `/agk:wsl` (set up, or resume a stopped run), `/agk:wsl status` and `/agk:wsl back` (return to
Windows). The machine work is one kit script, `wsl_setup.ps1`, run from this plugin and never installed into the
project; every step checks first and skips what is done, so running it again resumes. It never asks for, stores or
prints a password or a sign-in secret. Save each `-Json` output to a file in the temp folder; `<state>` is that file.

## /agk:wsl status

1. Run the checks only, then the status lines, and show them in plain words: WSL and its memory, the sign-ins, the
   clone and its worktrees, the adapter on the default branch, which watchdog is active, Podman and Playwright, and the
   doctor's verdict. Change nothing. Pass `-Engine <engine>` when the state of an earlier run names one.

   ```
   pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl_setup.ps1" -Status -Json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl.py" status --state <state>
   ```

## /agk:wsl

1. The script reads the project's remote, the git name and email and the machine's memory itself. Ask the person
   nothing else unless a step below says so.
2. Show the plan (five lines or fewer) and the container engine lines, and ask for a yes and for the engine; on
   anything but a yes, stop. The engine lines name what the project's files and this machine use and recommend one
   with its reason (Podman when nothing decides); the person may choose `podman`, `docker` (Docker Engine inside WSL)
   or `docker-desktop` (Docker Desktop's WSL integration, never installed by the kit), and for `docker` the group or
   `--rootless`. Show the Docker Desktop line as printed: it points to Docker's page and states no licence terms.
   Show the volume lines as printed: nothing is moved; the person runs the export and import commands if they want
   their data in WSL.

   ```
   pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl_setup.ps1" -Status -Json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl.py" plan --state <state>
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl.py" engine --state <state> [--choose <engine>] [--rootless]
   ```

3. Run the setup with the chosen engine (`-Engine <engine>`, and `-DockerRootless` when the person chose rootless;
   add `-InstallWatchdog` only when the plan's watchdog line says the WSL task goes on: that pass also stops the
   Windows engine, never uninstalling it), then show the status lines. When `one_engine` waits, Docker Desktop is
   running: tell the person to quit it (it stays installed); two engines never share the ports.

   ```
   pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl_setup.ps1" -Engine <engine> -Json
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl.py" status --state <state>
   ```

   For each step that says `waiting`, tell the person exactly what its note says and where: the GitHub and Claude
   sign-ins are the normal sign-ins in the browser, started in the `AGK shell (WSL)` tab of Windows Terminal. When
   `packages`, `gitleaks`, `gh_cli` or `nodejs` failed with a note about a certificate, ask the person for the path of
   the company root certificate and run the setup again with `-CorpCaFile <path>`. When a step needs a restart of Windows
   or a new window, say so and stop; the next `/agk:wsl` resumes.
4. When every step is done or skipped and the plan's line says `pull request`, prepare the one adapter pull request
   in the clone inside WSL (the folder the status names), running each command there with
   `wsl.exe -d <distro> --cd <folder> -- bash -lc "<command>"`:
   1. `git fetch origin`, then `git switch -c agk/wsl-adapter origin/<default branch>`. If the branch exists or the
      working tree has changes, stop and tell the person; never stash, reset or delete.
   2. Write the change, the project's ADR (Proposed) and the body. `--brief` takes the brief the work answers, or
      `none` when the person says the repository has no open brief. Edit no other protected path and never set the
      ADR `Accepted`.

      ```
      python3 "$(wslpath -a '${CLAUDE_PLUGIN_ROOT}')/scripts/agk/wsl.py" pr --to wsl --brief <n|none>
      ```

   3. Show what it printed: the changed files, the commit message, the body file and the commands that follow. The
      person commits with that message, runs `python3 scripts/agk/prepush.py --record --body <body file>`, pushes the
      branch and opens the draft pull request with `wsl.py open`, as printed. Stop there.
5. Tell the person: after the pull request merges, run `/agk:wsl` again; it moves the watchdog into WSL and disables
   the Windows task (never deletes it). In personal mode, or with `auto_start` off, there is no watchdog step.

## /agk:wsl back

1. Show the plan and ask for a yes; on anything but a yes, stop:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl.py" plan --back
   ```

2. When the plan says `pull request`, prepare the reverse pull request as in step 4 above, in the Windows checkout,
   with `wsl.py pr --to windows` and the branch `agk/windows-adapter`.
3. When the plan's watchdog line says the Windows task is re-enabled, run the script's back form with the engine of
   the state and show the result: it also starts the Windows engine again. The clone inside WSL stays; nothing is
   deleted.

   ```
   pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl_setup.ps1" -Back -Engine <engine> -Json
   ```

Never merge, never enable auto-merge, and do not commit or push: the person does, and reviews and merges the pull
request. Do not set a spec `Approved` or an ADR `Accepted`.

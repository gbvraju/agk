---
name: wsl
description: Move this Windows machine's AI workforce into WSL 2 and back (agk wsl), with the checks, the sign-ins, the launch-adapter pull request and the watchdog done for the person. Never merges.
disable-model-invocation: true
argument-hint: "[status | back]"
---

# /agk:wsl

Run it from Claude Code on the Windows host, in the project's Windows checkout (`claude "/agk:wsl"`, or typed in a
session). Three forms: `/agk:wsl` (set up, or resume a stopped run), `/agk:wsl status` and `/agk:wsl back` (return to
Windows). The machine work is one kit script, `wsl_setup.ps1`; every step checks first and skips what is done, so
running it again resumes. It never asks for, stores or prints a password or a sign-in secret. Below, `SCRIPT` is
`pwsh -NoProfile -File "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl_setup.ps1"` and `HELPER` is
`python "${CLAUDE_PLUGIN_ROOT}/scripts/agk/wsl.py"`.

## /agk:wsl status

1. Run `SCRIPT -Status -Json`, save its output to a file in the temp folder, then run `HELPER status --state <file>`.
   Show the lines it prints in plain words: WSL and its memory, the sign-ins, the clone and its worktrees, the adapter
   on the default branch, which watchdog is active, Podman and Playwright, and the doctor's verdict. Change nothing.

## /agk:wsl

1. Read what the script needs yourself: `git remote get-url origin`, `git config user.name` and
   `git config user.email` (the script reads the same itself when they are not passed). Ask the person nothing else.
2. Run `SCRIPT -Status -Json` to a file, then `HELPER plan --state <file>`. Show its lines (five or fewer) and ask
   for a yes. On anything but a yes, stop.
3. Run `SCRIPT -Json` (add `-InstallWatchdog` when the plan's watchdog line says the WSL task goes on) to a file,
   then `HELPER status --state <file>`, and show the result. For each step that says `waiting`, tell the person
   exactly what its note says, and where: the GitHub and Claude sign-ins are the normal sign-ins in the browser, in
   the `AGK shell (WSL)` tab of Windows Terminal. When a download failed (`packages`, `gh_cli` or `nodejs` failed with
   a note about a certificate), ask the person for the path of the company root certificate and run the script again
   with `-CorpCaFile <path>`. When a step needs a restart of Windows or a new window, say so and stop; the next
   `/agk:wsl` resumes.
4. When every step is done or skipped and the plan's line says `pull request`, make the one adapter pull request in
   the clone inside WSL (the project folder the status names), with each command run through
   `wsl.exe -d <distro> --cd <project folder> -- bash -lc "<command>"`:
   1. `git fetch origin` and `git switch -c agk/wsl-adapter origin/<default branch>`; if the branch exists or the
      working tree has changes, stop and tell the person; never stash, reset or delete.
   2. `python3 "$(wslpath -a '${CLAUDE_PLUGIN_ROOT}')/scripts/agk/wsl.py" pr --to wsl --brief <n|none>` (this
      plugin's copy, read from inside WSL; the brief the work
      answers, or `none` when the person says the repository has no open brief). It changes `launch_adapter` in the
      `[flow]` table, writes the project's ADR (Proposed) and prints the body file. Edit no other protected path
      and never set the ADR `Accepted`.
   3. `git add -A`, `git commit` with the printed commit message, then `python3 scripts/agk/prepush.py --record --body
      <body file>`; on a failure stop and show it.
   4. `git push -u origin agk/wsl-adapter`, then `wsl.py open --body <body file> --branch agk/wsl-adapter`. Show the
      address it prints and stop. Never merge, never enable auto-merge.
5. Tell the person: after the pull request merges, run `/agk:wsl` again; it moves the watchdog into WSL and disables
   the Windows task (never deletes it). In personal mode, or with `auto_start` off, there is no watchdog step.

## /agk:wsl back

1. Run `HELPER plan --back` and show its lines; on anything but a yes, stop.
2. When the plan says `pull request`, make the reverse pull request as in step 4 above, in the Windows checkout,
   with `wsl.py pr --to windows` and the branch `agk/windows-adapter`.
3. When the plan's watchdog line says the Windows task is re-enabled, run `SCRIPT -Back -Json` and show the result.
   The clone inside WSL stays; nothing is deleted.

Do not merge. Do not set a spec `Approved` or an ADR `Accepted`. Never merge or enable auto-merge on the pull
request: the person reviews and merges it.

# Remote builders: run builder sessions off your laptop

A builder session and its heavy checks can run in a remote development environment instead of on your own machine. Your laptop
then runs only your own tools, and nothing is lost when a remote session stops, because a session keeps all of its state on
GitHub and resumes from there (REQ-040, brief #375).

Why: in a pilot, two builders and their heavy test runs shared one laptop with the person's own work, and the machine ran out of
memory and stopped a builder's watch without anyone noticing. A remote environment gives each builder its own memory and disk, and
a stop costs nothing but a restart.

This guide names no provider. Any remote development environment that gives you the capabilities below will do.

## What a remote builder needs

- **A git checkout of its own.** One clone of the repository per builder session, never shared with another session or with
  your own working copy, on a disk that holds the project's heavy checks.
- **python3**, 3.11 or newer, for the kit's scripts.
- **`gh` signed in with a builder token**, not with your own account's sign-in. The token can push branches, open pull requests
  and post comments on the one repository, and nothing more: it cannot merge, cannot approve, cannot change settings, rulesets,
  secrets or workflows of the repository. Make it for this purpose and give it the shortest lifetime your work allows.
- **The project's toolchain**: whatever `make test` and the project's own tests need (compilers, package managers, the
  project's dependencies), installed in the environment, so that `python3 scripts/agk/prepush.py` runs there as it runs for
  you.
- **A way to keep a command running in the background** while the session waits, so that `session.py watch` can wake the
  session (session rule 10), and network access to GitHub.

## Start and resume

A remote builder starts exactly as a local one, from GitHub alone:

1. Clone the repository into the environment and run `git fetch origin <default branch>`, then
   `python3 scripts/agk/doctor.py --paused --ref origin/<default branch>`; stop if it prints `agk paused` (session rule 33).
2. Find the next item with `python3 scripts/agk/session.py next --session <id>`, or take the item the conductor assigned with
   `python3 scripts/agk/session.py claim --session <id> --brief <n>` (session rules 5 and 18).
3. Build it test-first on its own branch, checkpoint and push as the session rules say, and wait for the verdict with
   `python3 scripts/agk/session.py watch --pr <n>` in the background.

Nothing the session needs lives only in the environment: its claim, its pull request, its `Progress:` line, its reports and its
verdicts are all on GitHub. So a stopped or reclaimed environment loses nothing that was pushed:

- A session that restarts on its own open pull request runs `python3 scripts/agk/session.py resume --pr <n>` and carries on
  from the `next:` step of its progress line (session rule 9).
- A session whose pull request has merged runs `python3 scripts/agk/session.py after --session <id>` and does what it prints
  (session rule 18).
- A session that comes back after GitHub could not be reached pushes its local commits first, then posts the `Report:` or
  `Question:` it could not post (session rule 23).

Only work that was never pushed is lost when an environment stops, which is why a builder pushes a `checkpoint:` commit at each
step that leaves its tests green or expected-red (session rule 7).

## What stays on your machine

These stay with you and never move into the remote environment:

- **Review and approval**: the conductor's verdicts and every person's approval (`Approve:`, and in solo mode `Confirmed:`)
  are given from your own account, on your machine or in the browser.
- **Merge**: a person merges, from their own account; a builder never merges and its token cannot.
- **Secrets**: the project's production secrets, your own GitHub sign-in, and any admin or owner credential.
- Changes to the repository's settings, rulesets and workflows, which need an admin.

## Safety rules

1. The remote environment holds **no production secret**: no deployment key, no customer data, no credential of a live
   service. If the project's tests need a service, they use a stand-in there, as they would in CI.
2. The remote environment holds **no admin token**: no token that can change the repository's settings, rulesets, secrets or
   members.
3. A session's token **can only push branches and comment**: push to its own branch, open its pull request, and post its
   `Report:`, `Question:`, `Progress:` and claim comments. It cannot merge, approve or push to the default branch.
4. The environment is **stopped when idle**: when its session has ended, or has waited a long time with nothing to do, stop it,
   so that no forgotten machine keeps a token alive.
5. Your own sign-in is **never copied into it**: not your GitHub sign-in, not your session cookies, not your keys. The builder
   token is the only credential in the environment, and you revoke it when the work is done.

Because a session keeps its state on GitHub, stopping an environment under rule 4 is always safe once its work is pushed.

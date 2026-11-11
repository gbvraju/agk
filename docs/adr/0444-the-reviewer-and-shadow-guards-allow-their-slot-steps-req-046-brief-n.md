# ADR-0444: The reviewer and shadow guards allow their slot steps

- Status: Proposed
- Date: 2026-11-11
- Deciders: maintainers
- Related: brief #1050, plan #661, brief #1013, brief #1014, ADR-0431, Q-1013-3, Q-1014-1
- Requirements: REQ-046, REQ-054

Protected classes: `.claude/`, `config/`, `tests/kit/`

## Context

`architect-review.md` names the steps of a reviewer slot run (ADR-0431): check out the head, save the review
bundle, write the verdict to a file, check it with `conductor.py check-verdict`, post it and release the slot. On
the default branch the review agent's guard (`architect_guard.py --review`) denied every write and every one of
those commands, so no reviewer slot could run. The shadow's guard (`conductor_guard.py --shadow`) allowed no
`session.py` command, so the shadow could take no slot. The owner ruled Q-1013-3 (the review agent writes in one
scratch folder outside the project, the conductor guard's limit) and Q-1014-1 (the shadow runs `session.py slot`).

## Decision

1. In review mode only, `Write` is allowed to a regular file inside `agk-review-<name>` directly in the system temp
   directory and outside the project, judged by real path, with no link and no `..` out of it. `Edit`, `MultiEdit`,
   `NotebookEdit` and every other `Write` stay denied.
2. In review mode only, exactly these commands are allowed, with no shell operator: `git fetch origin`;
   `git checkout --detach <sha>` with the sha 7 to 40 lower-case hex characters and on a branch of origin;
   `python3 scripts/agk/conductor.py check-verdict <file> --pr <n>`; a comment `POST` to the origin's issue comments
   with the one field `-F body=@<file>` whose first line is a `Verdict:` line; and
   `python3 scripts/agk/session.py slot (--next | --release) r<N>`. Each file is an existing regular file of a review
   scratch directory.
3. In shadow mode only, exactly `python3 scripts/agk/session.py slot --next s-shadow` and `... --release s-shadow`
   are allowed, the project's own regular script. Every other `python3` command stays denied there.
4. The conductor's post of `Shadow: s-shadow #<pr> <sha>` was already allowed (`Shadow:` is not a line its verdict
   check reads); no code changes for it, and a test pins it.
5. The scratch test is copied into the architect's guard with the review name, because the conductor's guard
   imports the architect's. The on-origin test is the conductor guard's own `on_origin_branch`, imported late, at the
   one checkout step, so the architect's guard holds no command of its own and there is no import cycle.

6. The owner's edit of `.claude/agents/conductor.md` on this branch (Q-1050-2) leaves the file at 4499 words, so its
   line in `config/rule-budget.txt` is lowered from 4500 to 4499, as that file requires of a cut file in the same pull
   request (ADR-0310). No other budget line changes.

## Consequences

A reviewer slot and the shadow slot can each run under their own guard, so gate review's fresh reviewer and its
blind shadow can both run. Without `--review` and `--shadow` the guards are unchanged. In review mode the guard now
runs one local `git branch -r --contains` (through the conductor guard) at a checkout, as the conductor's guard does
at a worktree add; the hook itself still makes no network call. After the allowed checkout of a head into the project,
`conductor.py check-verdict` and `session.py slot --release` run that head's own versions of those scripts, with the
reviewer's environment and GitHub access, not under the conductor's `env -i` bounded run in a separate worktree. The
only bound is the origin-branch check, which refuses a fork's head.

## Residual

- 2026-11-11: the owner added the conductor's `Shadow:` sentence on this branch (Q-1050-2); the review role file's
  "no write until Q-1013-3" stays the owner's to edit (brief #1050 answer 6); `session.py slot` on the default branch accepts no
  `s-shadow` name yet, so the shadow's slot runs once a brief adds that name; the guard cannot tell the pull request
  under review from another issue without a network call, so the comment's target stays the role file's rule.
- 2026-11-11: a later brief may run the reviewer slot's `check-verdict` and `slot --release` from the default branch's
  copy of the scripts (or under `env -i`), so that the reviewed head's code does not run with the reviewer's access.

# ADR-0272: session.py tidy removes finished builder worktrees and branches (REQ-040, brief 548)

- Status: Proposed
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0182, ADR-0191, ADR-0264
- Requirements: REQ-040

Protected classes: `scripts/agk/`, `tests/kit/`, `.claude/`

## Context

In local mode every builder session gets a worktree and a `claude/brief-<n>` branch, and nothing in
the kit removes them after the pull request merges; the owner counted 60 at one time (brief #548).
`git branch -d` refuses a squash-merged branch, so tidying by hand is slow and risky. This ADR
number was reserved for brief #548 by the conductor (the field note on #548); it is a fix under
plan #542, with no new capability.

## Decision

1. `python3 scripts/agk/session.py tidy [--apply] [--json]` lists every linked worktree and every
   local branch. Without `--apply` it changes nothing: one line `remove <path> <branch> #<pr>
   merged|closed` per candidate (`-` for a branch without a worktree) and one line `kept: <reason>
   (<path> <branch>)` per item kept. With `--apply` it removes exactly the candidates and prints
   `removed ...` for each.
2. An item is a candidate only when all of these hold, checked in this order, the first that fails
   being the reason printed: not the main clone (`main clone`), not the current worktree (`current
   worktree`), not locked in `git worktree list --porcelain` (`locked`), on a branch (`no branch`)
   that is not the default branch (`default branch`), its worktree has an empty
   `git status --porcelain` (`uncommitted files`; a status that cannot be read is
   `could not read the worktree`), no live lock owner record and no queue job names its session
   (`running`), its branch's pull requests read with one REST GET
   (`repos/{repo}/pulls?head=<owner>:<branch>&state=all`) include none that is open (`open pull
   request`), at least one (`no pull request`), and the read succeeded (`could not read GitHub`),
   and the branch tip equals the newest pull request's head sha (`commits after the pull request's
   head`). A read failure keeps the item; it never counts as merged.
3. Running: the lock folders `agk-lock-*` beside the heavy lock (`lock_dir` of agk.toml, or the
   temp folder) whose owner record `lock.py` does not judge stale, and every job file of a
   `.agk-lock-*.queue/jobs/` folder. A record names an item when its session is the branch, the
   branch's last part or the worktree's folder name, appears in the worktree's path, or shares a
   number with the branch (`b548` and `claude/brief-548`); a job also by its branch or folder. A
   live record with no session, or an owner file that cannot be read, names every item.
4. Removal: `git worktree remove <path>` (never `--force`; git itself refuses a dirty tree), then
   `git worktree prune`, then `git branch -D <branch>` only after the tip is read again and still
   equals the head; each is one argument list with the path as git listed it, never a shell
   string, so long and 8.3 Windows paths pass unchanged (#508). A failed step keeps the item and
   skips its branch. Remote branches are never deleted.
5. `tidy` is refused while the kit is paused (session rule 33: nothing is deleted while paused).
6. `doctor.py` prints `tidy: <n> finished worktrees; run session.py tidy` when more than five
   linked worktrees are candidates; with five or fewer linked worktrees it reads nothing more.
7. The conductor runs `python3 scripts/agk/session.py tidy --apply` once at the start of its
   session and after each merge it makes; its guard allows exactly that form. A builder never
   runs `--apply`.

## Consequences

Finished builders no longer pile up, and nothing unsaved, open or running is removed. A worktree
whose session name shares no part with its branch or path is matched only by a live record with no
session; a lock held by such a session for another worktree does not keep it, which is why git's
own refusal of a dirty tree stays the last guard.

## Residual

- 2026-11-04: the session-to-worktree match of decision 3 is by name (Q-548-1); a lock owner record
  that names its worktree would make it exact.

# ADR-0551: Sessions never build in the shared main folder

- Status: Accepted
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0237, ADR-0525, ADR-0531, SPEC-0050, brief #1301, plan #661
- Requirements: REQ-039

## Context

In a customer project on the kit 0.64.2 in local mode (Windows, one clone shared by a conductor, two builders that the launch
adapter started in their own worktrees, and a helper session opened by hand), the helper built a pull request in the main
folder and left it on its branch with an untracked file. For about two hours the conductor read that builder branch as its
checkout: the planner printed false `MALFORMED` lines for two briefs (an `Adds:` file that existed only in that folder), and
the owner had to find and switch the folder back by hand. Builders the adapter starts were never affected; only a session
opened by hand in the main folder did this.

## Decision

1. `common.shared_main(root)` (imported by `scripts/agk/session.py`) is true when ROOT is the clone's main worktree (its git
   directory is the common directory) and the clone is shared by sessions (`common.clone_shared_by`): `execution = "local"`,
   or a `[flow] launch_adapter` is set, or another worktree whose folder is named `agk-*` exists. The adapter setting does not
   count in a cloud session (`CLAUDE_CODE_REMOTE=true` (verify)), whose clone is its own (the brief's mode check CI,
   Q-1301-1). There, `session.py claim` and `next --take` (and so `after`) refuse with `refused: this is the main folder that
   other sessions read; start in your own worktree (git worktree add ../agk-<session> origin/<default branch>)` and the
   setting in brackets, exit 1, before any read of GitHub; `prepush.py` refuses the same way (exit 2) unless the folder is on
   the default branch. In personal mode (a `[personal]` table) the line starts `warning:` and nothing is refused.
2. `.claude/hooks/stop_check.py` first prints, on standard error, `main folder: on <branch>, <n> untracked; switch back with
   git checkout <default branch>` when the main folder of such a clone is off the default branch or holds untracked files
   outside the ignored paths (`git ls-files --others --exclude-standard`); what the hook decides is unchanged.
3. `scripts/agk/conductor.py sweep` and `scripts/agk/doctor.py` print `MAIN-FOLDER: on <branch>, <n> untracked` in the same
   case, information only. The planner's brief shape (`session.brief_shape`) reads the files for the `Adds:` check from
   `origin/<default branch>` (`session_plan.touch_rules(root, ref)`, `git ls-tree`), never from the main folder's working
   files; a ref git cannot read falls back to the checkout's list, as before. `check_brief.py` and `doctor.py`'s broad-touches
   check are unchanged.
4. `docs/guides/local-mode.md` and `docs/guides/getting-started.md` state the rule: the main folder stays on the default
   branch and is only pulled; every session starts in its own worktree.

No workflow file, ruleset, `constitution/` file or spec changes.

## Consequences

In local mode a session opened by hand in the main folder is refused at its first take and its first push, and the folder's
drift is reported at once by the stop hook and in the conductor's sweep; the planner no longer reads a builder branch's files.
In CI mode (each cloud session has its own clone) nothing is refused. In personal mode the session is warned only. Tests:
`tests/kit/test_shared_main.py`. Protected path classes changed: `scripts/agk/` (`scripts/agk/common.py`,
`scripts/agk/session.py`, `scripts/agk/session_plan.py`, `scripts/agk/prepush.py`, `scripts/agk/conductor.py`,
`scripts/agk/doctor.py`), `.claude/` (`.claude/hooks/stop_check.py`), `tests/kit/` (`tests/kit/test_shared_main.py`) and `agk.toml` (the new test
file added to the `[[testing.map]]` entries of `scripts/agk/session.py` and `scripts/agk/session_plan.py`, which
`tests/kit/test_always_full_infra.py` requires).

## Residual

- 2026-11-14: the conductor's role file `.claude/agents/conductor.md`, which would put `MAIN-FOLDER:` lines under `Needs a
  fix`, is not changed here: it is not among the brief's `Touches:` (Q-1301-2).
- 2026-11-14: the helper lives in `scripts/agk/common.py`, imported by `session.py`, so that the stop hook, `prepush.py`,
  `conductor.py` and `doctor.py` share it without importing `session.py` (Q-1301-3).

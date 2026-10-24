# ADR-0105: the conductor role file and its guard hook (REQ-037 part b2, SPEC-0030 rule 6)

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0100, ADR-0102, ADR-0098
- Requirements: REQ-037

Protected classes: `.claude/`, `kit/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0030 (Approved, #167) rule 6 and the verdict on #172: this is build (b2), the conductor role file and its guard, measured before it was started (about 60 lines of role file, 70 of guard and 330 of tests). The architect's seven pre-verdict steps on issue #163 are in the role file. The tests were written first (`tests/kit/test_conductor_guard.py`, `tests/kit_dev/test_conductor_role.py`; on the unchanged tree: 58 failed).

## Decision

1. **`.claude/agents/conductor.md`** (installed, verbatim): tools `Read, Grep, Glob, Bash, Write`; reviews every open pull request of the queue by the architect's protocol (the block between the markers is the architect's, verbatim); posts one verdict comment on each; orders the queue by `Depends-on`; runs the seven steps before every verdict, in the order of the architect's comment; edits no file; never merges, tags or enables auto-merge.
2. **`.claude/hooks/conductor_guard.py`** (installed, verbatim): `Edit`, `MultiEdit` and `NotebookEdit` are refused everywhere and `Write` outside a scratch directory (`agk-conductor-<name>` directly in the system temp directory, outside the work tree, links resolved); `Bash` only for read-only `git`, `git fetch origin`, `gh api` GET, the one comment POST on the origin repository (`-f` fields only), `date -u` and the bounded run of the verdict on #175 (item 2): `git worktree add <scratch> <sha>` for a sha on a branch of `origin` (a fork's head is on none), `git worktree remove`, and, with the exact prefix `env -i PATH="$PATH" HOME=<scratch>` (the run's own scratch directory), `make -C <scratch> test|governance` and `python3 -I <scratch>/scripts/agk/<name>.py`; PATCH, PUT, DELETE, other POSTs, other scripts and `make` are refused naming rule 6, never the command. It imports the judging of `git` and `gh api` from `architect_guard.py` (Q-K4-266).
3. Flow mode: no version bump, one line under `## Unreleased` of `CHANGELOG.md`, manifest and hashes refreshed. Amendment 53 (`docs/runs/proposed-spec-amendments-53.md`) is applied to SPEC-0030; it also records that the learnings of issue #163 are later parts.

## Consequences

- A conductor session can read everything and post comments and nothing else; a verdict by it counts only when `verdict_authors` lists its account.
- `architect_guard.py` and `conductor_guard.py` must be installed together; both are in the manifest.

## Residual

- 2026-10-24: in an untrusted folder or a `-p` session the frontmatter hooks of a project agent do not run, so the guard does not run there; the account boundary (lane F: the conductor's account cannot merge or push) is then the only enforcement. The role file tells the person to accept the workspace trust dialog first (due 2026-12-31).
- 2026-10-24: the bounded run is not a sandbox; the pull request's code runs with the person's file permissions and can read files by absolute path, which is why it is allowed only for heads on a branch of `origin` (written by the project's own sessions) and why the account boundary of lane F stays the real enforcement; a container or sandbox for the run is the stronger form (due 2026-12-31).

# ADR-0688: The steward lands on the default branch, or stops

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1583 (its second pull request), SPEC-0066 rule 3 (build (d)), ADR-0663 (decision 6 plans this split), ADR-0662, Q-1583-1
- Requirements: REQ-073

## Context

ADR-0663 built SPEC-0066 rules 2, 4, 8 and 11 and left rule 3, the default-branch check and its `SessionStart` hook,
to this second pull request. Today `steward.py start` reads no branch. A person who opens the steward on a feature
branch, behind `origin` or in a builder's worktree gets no warning. A person who chose plain Claude gets none either.
ADR-0663 is merged and its `Final:` line is recorded, so this part takes its own ADR (the answer to Q-1583-1).

## Decision

1. **The check** (rule 3). `common.branch_check` reads where the steward was opened. It changes nothing except, on a
   fetch, the remote-tracking branch.
   - In the main folder, after one `git fetch origin <default branch>`: on the default branch and not behind `origin`
     it returns nothing. Off that branch, or behind, it returns one line, `branch: <where>; fix: git switch <default
     branch> && git pull --ff-only`. With uncommitted changes the line names their count and asks to keep them or set
     them aside first.
   - In a linked worktree it names the owner from an `agk-<session>` folder (else `another session`) and asks for
     the main folder. The steward's own `agk-steward` worktree goes on.
   - Outside git, or with no `origin`, there is nothing to check.
   - A main-folder branch of an open builder pull request reads as another branch. It is not looked up on GitHub.
2. **Where it runs.** `steward.py start` runs the check first and stops, exit 1, before any write. `steward.py
   branch` runs it again when the person asks the steward to act, and prints `branch: ok` or the line (exit 1). The
   role file names the guide in one line. The guide's new section `Off the default branch` in
   `docs/guides/steward-first-run.md` runs the fix only on the person's yes, and only with no uncommitted change.
3. **The start hook** (rule 3). `.claude/hooks/branch_check.py` is a new verbatim hook. It prints the same line on
   standard output, with no fetch, and prints nothing on the default branch. It always exits 0. It gives no line to a
   kit start whose `AGK_AGENT` names another role (ADR-0662), since that start is a builder, conductor or reviewer on
   its own branch.
4. **Installed with the agent line** (rule 2's writer). `common.with_agent`, the one writer that `init`, `adopt` and
   `upgrade` share, also writes the hook's `SessionStart` entry as the first entry of `hooks` in the project's copy.
   `common.without_agent` takes the entry away together with the agent line. The kit's own copy therefore holds
   neither, and its bytes and hashes do not change. The manifest's `project_keys` names both keys: `agent` and
   `hooks.SessionStart`. An upgrade that writes no agent line (rule 11) writes no hook either.

Protected path classes changed: `scripts/agk/` (`common.py`, `steward.py`), `.claude/` (`.claude/hooks/branch_check.py`,
new, and `.claude/agents/steward.md`, one line), `kit/` (`kit/manifest.json` and the `gitattributes` template, which
pins the hook LF), `config/` (the steward's line in `config/rule-budget.txt`, 966 to 972 words), `agk.toml` (the
hook's `[[testing.map]]` entry), `tests/kit/` (`test_first_open.py`) and `docs/adr/` (this file).

## Consequences

A project installed or upgraded by this release tells the person in one line when the steward or a plain session opens
off the default branch, and changes nothing until they say yes. A kit-started builder or conductor gets no line. A
project whose upgrade withholds the agent line (ADR-0663 decision 2) gets no hook until its adapters pass `--agent`.

## Residual

- 2026-11-21 (verify): that a `SessionStart` hook's standard output is shown to the person at session start, and that a
  kit start's `AGK_AGENT` reaches the hook's environment, are read from a recorded run (due 2027-01-31).
- 2026-11-21: personal mode runs the same check. A developer on a feature branch of the product is told so at the
  steward's start. Whether personal mode should skip it is left to the maintainers.

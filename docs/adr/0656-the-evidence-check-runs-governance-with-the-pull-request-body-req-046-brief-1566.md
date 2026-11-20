# ADR-0656: The evidence check runs governance with the pull request body

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: ADR-0233, ADR-0271, ADR-0542, ADR-0550, SPEC-0039, brief #1566, plan #661
- Requirements: REQ-046

## Context

`scripts/agk/evidence.py check` runs governance in a worktree of the head with the conductor's environment: `PATH`, a
scratch `HOME` and `AGK_BASE` only (brief #1291, ADR-0550). `check_protected_changes.py` reads the pull request body from
`--body FILE` or the file `AGK_PR_BODY` names (brief #545, ADR-0271), and without either a protected change that only a
`Covered-by:` line covers fails. The builder's `prepush.py` runs governance with the body (session rule 31), so the
builder's record and the conductor's evidence check disagreed on every head that relies on `Covered-by:`, and the merger
held each such head (`evidence differs (rule 4)`) until the owner posted an accept for it: two accepts on #1544 on
2026-11-20, both for heads whose only failing step was protected-changes without the body. Measured on head 069ea584 of
#1544 (brief #1566, before any change): `check_protected_changes.py` with the conductor's environment fails both classes;
the same command with `AGK_PR_BODY` set to the pull request's body passes.

## Decision

1. `evidence.py check` takes `--body FILE`, at most once. The file is read as UTF-8 text of at most 65536 characters
   (GitHub's limit for a body). The check copies its bytes into its own temporary folder, beside the worktree, and adds
   `AGK_PR_BODY` naming that copy to the governance environment of ADR-0550, so the fixed list gains that one name and
   never the person's path; the copy is removed with the folder. The sampled re-runs keep the record's environment
   (`run_env`), and the record's `pr-body` unit still re-runs only on its recorded path.
2. A body that cannot be read (missing, a folder, not UTF-8, over the limit) prints `evidence: the pull request body
   cannot be read (option: --body)`, naming the option, never the path or a value; it is a finding like `stale`, so
   nothing is re-run and the check reports `differs` (exit 1), never `agrees`.
3. The `Evidence check:` line ends `, body <sha12 of the file>` when the body is given and `, body not given` without it,
   so a `differs` caused by a missing body is explained in the verdict; `--json` adds `body_sha256` (or null). The
   merger's reading of the line (`Evidence check: agrees|differs, head <sha12>`) is unchanged.
4. The conductor's local-mode step (`.claude/agents/conductor.md`) runs `evidence.py check --head <sha> --body <file>`,
   the file the pull request body it read with one GET, written to its scratch directory. Its guard
   (`.claude/hooks/conductor_guard.py`, ADR-0542) allows `--body` once, with an absolute path of an existing regular file
   of a scratch directory, never a link, the clone's shared evidence folder or another path.
5. Nothing else changes: the merger's hold of rule 4 stays as it is (Q-1566-1); hosted mode runs no evidence check;
   personal mode (`forge = "files"`) runs none either and its gate uses only `evidence.parse` and `evidence.problems`,
   whose forms do not change. No workflow file, ruleset, `constitution/` file or spec changes.

## Consequences

In local mode a head whose protected change a `Covered-by:` line covers agrees with its record when the conductor passes
the body, so with `[flow] auto_merge = true` it merges without an owner accept; with `auto_merge = false` only the
verdict's line changes. A `Covered-by:` that names an ADR not Accepted on the merge base still fails governance, as
before (principle 11). A conductor that omits `--body` gets today's result, explained by `body not given`. Tests:
`tests/kit/test_evidence.py` and `tests/kit/test_conductor_guard.py`.
Protected path classes changed: `scripts/agk/` (`scripts/agk/evidence.py`), `tests/kit/` (`tests/kit/test_evidence.py`,
`tests/kit/test_conductor_guard.py`) and `.claude/` (`.claude/agents/conductor.md`, `.claude/hooks/conductor_guard.py`).

## Residual

- 2026-11-20: the conductor writes the body it read to a scratch file; a body edited after that read is not the one
  governance sees until the next check (the verdict quotes the sha256 it used).

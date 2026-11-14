# ADR-0536: Local evidence lives in the clone's shared folder

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0208, ADR-0233, SPEC-0039, brief #374, brief #434, brief #982, brief #1269, plan #661
- Requirements: REQ-039

## Context

In local mode a builder records its run with `prepush.py --record FILE` (ADR-0208) and the conductor checks that record
with `evidence.py check RECORD --head <sha>` (ADR-0233). FILE could be any path, and `docs/guides/local-mode.md` only said to
keep it outside the repository and where the conductor can read it. In a customer project on v0.64.2 (local mode, Actions
disabled) a builder wrote its record to its own temporary folder; its `Evidence:` line names only the record's digest, so
the conductor could not find the file, its verdict had no `Evidence check:` line, and `merge_cleared.py` held a cleared,
green pull request with `no local evidence for this head` (rule 4). Any builder of any local-mode project can hit this.

## Decision

1. `scripts/agk/prepush.py`: `--record` with no FILE, or `--record auto`, writes the record to
   `<git common dir>/agk-evidence/<40-hex head>.json`, in the folder `git rev-parse --git-common-dir` names, made when
   missing. That folder is one per clone, shared by every worktree of it, never tracked and never makes the tree dirty.
   `--record FILE` works as before, and the `Evidence:` line is unchanged. A `--queue` run passes `auto` on unchanged, so
   the record is named by the head the job runs on.
2. `scripts/agk/evidence.py check`: RECORD is optional when `--head <sha>` is given; without it the check reads
   `<git common dir>/agk-evidence/<sha>.json` (the head resolved to its 40 hex characters), and when that file is missing
   it exits 3 with `evidence: no record for this head in the shared evidence folder (option: --record)`, naming the
   option, never a path. Without RECORD and without `--head` it stays a usage error (exit 2).
3. `.claude/hooks/architect_guard.py` (the review agent's guard, brief #982): the evidence check is allowed also with no
   RECORD and `--head <sha>`; `check` with neither stays denied.
4. `.claude/agents/conductor.md`, `docs/guides/local-mode.md`, `docs/guides/reference.md` and `docs/guides/testing.md`:
   in local mode the builder runs `prepush.py --record` with no FILE and the conductor's evidence check is
   `evidence.py check --head <sha>`; a session on another machine still passes a FILE and gives it to the conductor.

No workflow file, ruleset or `constitution/` file changes. In CI mode no record is read, so nothing changes there; in
personal mode a record, if asked for, goes to the same folder.

## Consequences

The conductor finds the builder's record from the head alone, so a cleared, green local-mode pull request is no longer held
for a record nobody can locate. Records of older heads stay in the folder until a person removes them; they are small and
named by head, so a stale one is never read for another head. The conductor role file stays within its rule budget (4498
words, 37 rules; `config/rule-budget.txt` lowered from 4499): the new clause is paid for by shortening the local-mode
paragraph without changing its rules. Tests: `tests/kit/test_evidence_location.py` (a) to (d), and two new cases in
`tests/kit/test_architect_review_guard.py`. Protected path classes changed: `scripts/agk/` (`prepush.py`, `evidence.py`),
`.claude/` (`.claude/agents/conductor.md`, `.claude/hooks/architect_guard.py`), `config/` (`config/rule-budget.txt`) and
`tests/kit/` (`test_evidence_location.py`, `test_architect_review_guard.py`).

## Residual

- 2026-11-14: the conductor's own guard (`.claude/hooks/conductor_guard.py`) allows no `evidence.py` command; only the
  review agent's guard does. Whether the conductor's guard should allow `check --head <sha>` is left to the maintainers
  (Q-1269-1, due 2026-12-31).

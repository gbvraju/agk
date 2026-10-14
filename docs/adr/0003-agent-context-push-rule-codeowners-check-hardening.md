# ADR-0003: Agent context, push rule, CODEOWNERS, check hardening

- Status: Proposed
- Date: 2026-10-14
- Deciders: maintainers
- Related: ADR-0001, ADR-0002
- Requirements: REQ-001, REQ-002, REQ-003, REQ-005, REQ-008

## Context

PR #1 review and the pre-publication pass found gaps: no agent context file that survives compaction, no
permitted push command, CODEOWNERS not committed, ADR cover that did not check what it covered, requirement
markers counted in any file, and a workflow that did not re-run when a PR body was fixed. This ADR adds decisions;
it amends no text of ADR-0001 or ADR-0002.

This PR changes these protected path classes, all named here: `CLAUDE.md`, `config/`, `.claude/`, `.github/`.

## Decision

1. **CLAUDE.md** at the repository root states the agent operating rules (day-0 §0 rules 1–9), points to
   `constitution/principles.md`, and carries a compaction-recovery block. It is added to
   `config/protected-paths.txt` and to the `protected` class in `config/reviewers.yaml`.
2. **Push rule.** `.claude/settings.json` allows exactly `Bash(git push -u origin HEAD)` and nothing broader. Deny
   rules still win over allow, and none of them matches that command. Edit rules for protected paths use the
   `ask` list and the `Edit(...)` form anchored at the project root (`/path`); `Write(...)` rules are
   removed because Claude Code consults only `Edit` and `Read` path rules. Verification is in `docs/runs/day-1.md`.
3. **CODEOWNERS** is the one exception to rule 5 (generated files are not committed): GitHub needs the file in the
   repository and it changes rarely. `.github/CODEOWNERS` is committed as rendered by
   `scripts/agk/reviewers.py --codeowners`; `--check-codeowners`, run by `make governance`, fails when the
   committed file differs from the rendering.
4. **ADR cover names the class.** `check_protected_changes.py` accepts an ADR as cover only when it is added or
   modified in the PR, is not a Status-only edit, and its text names every changed protected path class (the entry
   from `config/protected-paths.txt`).
5. **Markers only in test files.** `REQ-nnn` markers count only in files named `test_*.py` under the configured
   directories (Q-K0-12).
6. **Governance re-runs on PR body edits.** `.github/workflows/governance.yml` lists `edited` among the
   `pull_request` types, so fixing a PR body re-runs the body check without an empty commit.

## Consequences

- A protected change must be covered by an ADR that says which classes it touches; a drive-by ADR cannot cover.
- The committed CODEOWNERS can drift only until the next `make governance`, which fails.
- Marker counts fall to real tests; fixtures and notes no longer satisfy `done`.

## Residual

- 2026-10-14: colon-refspec branch deletion (`git push origin :branch`) has no deny rule; `main` is protected by the
  ruleset only. Revisit when `agk doctor` exists.
- 2026-10-14: GitHub Action versions stay on major tags until K1 exit, then SHA pins.

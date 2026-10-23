# Proposed spec amendments 41 (SPEC-0021 rules 4 and 8; SPEC-0012 rule 11; SPEC-0013 rule 11; REQ-028 part L3b)

Date: 2026-10-23 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0079. The paths: `docs/specs/0021-when-a-fix-list-verdict-s-only-item-is-the-final-commit-and.md`, `docs/specs/0012-intake.md`, `docs/specs/0013-playbook.md`.

1. **SPEC-0021 rule 4, the option that names the head.** The check takes `--comments FILE` and `--head SHA` (default `HEAD`), not `--base REF`: the workflow checks out a merge commit, so the pull request's head is named
   (Q-K4-231). It prints `ok final-clearance` or `FAIL final-clearance: rule 3 ...`, and `skipped (no comments file)` without the file. It is the tenth step of `make governance` and of the workflow.
2. **SPEC-0021 rule 8, the permission.** The workflow's `permissions` block gains `issues: read` and `pull-requests: read` (both read-only; Q-K4-230 ruled in the verdict on the build: grant both).
3. **SPEC-0012 rule 11, one status-line reader.** The final-commit mode of `intake.py` reads its status lines through `common.final_commit_problems`; what it accepts and prints is unchanged.
4. **SPEC-0013 rule 11, the verdict convention.** When the final commit is the only item, the first line is `Verdict: fix list <reviewed sha>` followed by `Final: <path> <old> -> <new>` lines and no numbered item (SPEC-0021 rule 1).

# ADR-0079: the covered final commit and its check (REQ-028 part L3b, SPEC-0021), kit 0.44.0

- Status: Proposed
- Date: 2026-10-23
- Deciders: maintainers
- Related: ADR-0066, ADR-0068, ADR-0078
- Requirements: REQ-028

Protected classes: `.claude-plugin/`, `.claude/`, `.github/`, `agk.mk`, `agk.toml`, `kit/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0021 (Approved, #99) lets a fix list whose only item is the final commit clear that commit in advance, and asks for a deterministic check that the commit changes only the named status lines. Its listed
verdict authors (rules 5 and 6) were built in L3a (kit 0.36.0). This part (L3b) builds rules 1 to 4 and 8 to 10: the covered fix list, the check, the workflow step, the verdict form and the shared status-line
reader. The measured clearance in the facts and the report (rule 7) is L3c. The tests were written first and run on unchanged `main` (32 failed; the output is in the pull request body).

## Decision

1. **The reader**: `common.covered_fix_list(body)` returns the reviewed sha and the `Final:` edits of a covered fix list or nothing; `common.status_edit` changes the one `- Status:` line of a file (of the named
   section of `docs/requirements.md`); `common.final_commit_problems` compares two commits with the edits applied. The final-commit mode of `intake.py` calls it (SPEC-0021 rule 10).
2. **The check**: `scripts/agk/check_final_clearance.py [--comments FILE] [--head SHA]` (installed verbatim) reads the comments (an array, arrays, pages or one object a line), takes the latest verdict by a listed
   author, and fails with `rule 3` when it is a covered fix list whose reviewed sha is the only parent of the head and the head is not exactly the named status lines (no other file, line, mode or rename). Anything
   else passes unchecked; without `--comments` it prints `skipped (no comments file)`. No network, no model.
3. **Governance**: the check is the tenth step of `agk-governance` and of the workflow. The workflow gains `pull-requests: read` (verify), one step that fetches the comments with `gh api --paginate --method GET`
   on pull requests, and the check step with `--head` set to the pull request's head. The workflow writes nothing to the pull request. A local `make governance` still prints nine `ok` lines and the `skipped` line.
4. **The form**: `kit/templates/playbook/verdict.md` and `.claude/agents/architect.md` describe `Verdict: fix list <reviewed sha>` with `Final: <path> <old> -> <new>` lines when the final commit is the only item.
5. **Amendment 41** (`docs/runs/proposed-spec-amendments-41.md`) is applied to SPEC-0021 rules 4 and 8, SPEC-0012 rule 11 and SPEC-0013 rule 11. The getting-started and existing-codebase guides and the security guide say
   the tenth line and the permission.
6. **Tests, first** (`tests/kit/test_final_clearance.py`, new, installed): the covered fix list and each refusal, the status edit, the check over a repository of dated commits (pass, each refusal, a later verdict, a
   stranger, no file, each comments-file shape, `--head` on a merge checkout), the workflow's permission and absence of writes, the make step, the texts, the shared function. The number of governance steps becomes ten in
   `tests/kit/test_workflow.py` and `tests/kit_dev/test_init.py`, which also gives the simulated CI run the comments file and the head.
7. **Kit 0.44.0**: the manifest `kit_version` and the new verbatim file, the hashes, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7).

## Consequences

- A project that upgrades gets the check and the workflow step; until a fix list with `Final:` lines is the latest verdict, it passes unchecked. The merge is still a person's.
- L3c (kit 0.45.0) follows with the measured clearance, and the report line that depends on it.

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-230 | SPEC-0021 rule 8 asks which permission lists a pull request's comments (`pull-requests: read` or `issues: read`) and to quote the page of GitHub's documentation. | `pull-requests: read` (the comments of a pull request are listed through `repos/<repo>/issues/<n>/comments`, which may need `issues: read` instead). The documentation host is not reachable from the build session, so no page is quoted and the choice is marked `(verify)` in the security guide and the amendment. Proposed for ruling. |
| Q-K4-231 | SPEC-0021 rule 4 names `[--base REF]`; the head of a pull request in the workflow is a merge commit. | The check takes `--head SHA` (default `HEAD`) and no `--base`: the reviewed sha and the head's only parent are all it compares. Proposed for ruling. |

## Residual

None.

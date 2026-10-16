---
name: review
description: Advisory review of one pull request with the project's reviewer subagent (review_context.py, check_review_report.py). Never an approval.
argument-hint: "[--base REF] PR_BODY_FILE"
---

# /agk:review

An advisory read of the current branch against its pull request body and the repository's Approved text. The result is
never an approval and human review stays required.

1. Make a directory in the system temporary directory; keep every file below in it, never in the repository.
2. Build the context from the pull request body file the user gives:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/review_context.py" --body PR_BODY_FILE
   ```

   Save the output as `review-context.md` in that directory.
3. Ask the project's `reviewer` subagent (`.claude/agents/reviewer.md`, installed by init and adopt) to review that file,
   and save its answer as `report.md` in the same directory. If the project has no `reviewer` subagent, stop and say so;
   this plugin ships none.
4. Validate the report:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/check_review_report.py" --context review-context.md --report report.md
   ```

5. Show the verdict and the findings. Do not post them anywhere and do not act on them.

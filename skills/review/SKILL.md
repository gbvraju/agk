---
name: review
description: Experimental, advisory review of one pull request with the project's reviewer subagent (review_context.py, check_review_report.py). Never an approval and never a gate.
argument-hint: "[--base REF] PR_BODY_FILE"
---

# /agk:review

An **experimental**, advisory read of the current branch against its pull request body and the repository's Approved text.
The reviewer agent is not installed by default (it caught 0 of 5 human findings in the shadow reviews). The result is
never an approval, never a gate and never counted as review; human review stays required.

Before anything else, check that the project has `.claude/agents/reviewer.md`. If it does not, stop and tell the user:
"The reviewer agent is experimental and not installed. To opt in, set `experimental_reviewer = true` in `agk.toml` and run
`/agk:upgrade`." Do not build a context, and do not copy the agent file yourself.

1. Make a directory in the system temporary directory; keep every file below in it, never in the repository.
2. Build the context from the pull request body file the user gives:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/review_context.py" --body PR_BODY_FILE
   ```

   Save the output as `review-context.md` in that directory.
3. Ask the project's `reviewer` subagent (`.claude/agents/reviewer.md`, installed only on opt-in) to review that file,
   and save its answer as `report.md` in the same directory. This plugin ships no reviewer.
4. Validate the report:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/check_review_report.py" --context review-context.md --report report.md
   ```

5. Show the verdict and the findings. Do not post them anywhere and do not act on them.

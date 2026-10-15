# Shadow review record (template)

SPEC-0003 rule 23. Before the reviewer agent is relied on, it shadow-reviews real pull requests alongside the human
reviewer. Copy this file to `docs/runs/shadow-review-<date>-pr<N>.md` (date from `date -u`) for each run. Nothing
the agent produces is committed except this record; the context and the report stay local files.

## How a run is made

1. Do not show the agent's report to the human reviewer and do not post it on the PR.
2. From a checkout of the PR head: `python3 scripts/agk/review_context.py --base origin/<default branch> --body
   <PR body file> > review-context.md`.
3. Ask the `reviewer` subagent to review `review-context.md`; save its answer as `report.md`.
4. `python3 scripts/agk/check_review_report.py --context review-context.md --report report.md`. A report that
   fails the validator is recorded as invalid with the validator's message, and counts as no verdict.
5. After the human reviewer has given a verdict, fill in the record below.

## Record

- PR: #N (title)
- Date of the run:
- Agent verdict:
- Context truncated: yes | no
- Findings: the numbered findings as validated (location, rule, wrong, fix), or `none`
- Human verdict (the `Review verdict (human):` line of the PR, or the comment):

### Agreements

Findings or verdicts where the human reviewer reached the same result.

### Misses

Defects the human found and the agent did not (one line each, with the rule that was broken).

### False positives

Findings the human reviewer rejected (one line each, with the reason).

### Footer

`<!-- agk-review: verdict=V findings=N truncated=B -->` as printed by the validator.

## Reading the records

The records are the evidence for whether the agent may be relied on. The maintainers decide (principle 1); the
agent does not.

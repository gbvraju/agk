# Shadow record

The record of the shadow reviews of the review protocol. Copy this file to `docs/runs/shadow-review-<N>.md`, repeat the section "Pull request" once for each pull request, and run
`python3 scripts/agk/shadow_count.py FILE` on it. The script reads that file only.

## Shadow session instructions

Start the review agent in a separate session (`claude --agent architect-review`) on the head the person reviews, blind both ways:

1. Post nothing on the pull request: no comment, no review, no reaction.
2. Do not read the pull request's comments or reviews. `gh api` GET reads the head, the diff, the specs and the checks, and nothing else.
3. The first line of the shadow verdict is `Shadow verdict: <cleared|fix list|rejected> <sha>`, never `Verdict:`. The verdict stays in the session's output.
4. After the person's verdict is posted, the maintainers paste both verdicts below, in batches, and mark each finding.

## What the numbers may say

A claim states the measured rate and nothing more. Below the person's rate the review agent is "a second reader", not "an architect". No model judges quality.

## Pull request {{n}}

### Person's verdict

```text
(paste the posted verdict)
```

### Shadow verdict

```text
Shadow verdict: cleared {{sha}}
```

### Findings

One line for each finding, in the form `- <by> <mark> <where>: <text>`: `<by>` is `both`, `person` or `shadow`; `<mark>` is `catch` or `false`; `<where>` is the rule or line the finding names.
A finding with no `<where>` counts for nothing.

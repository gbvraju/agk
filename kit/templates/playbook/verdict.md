Verdict: cleared {{sha}}

(The first line is exactly one of `Verdict: cleared <sha>` with at least 7 hex characters of the head at review time, `Verdict: fix list <sha>` or `Verdict: rejected <sha>`. A verdict that names another sha is void. After a blank line the verdict has these lines, in this order, then the findings; one sentence per finding, each naming a rule or a line. A later commit needs a new first line.)

Read: all (or the files read)

Rules:
- rule 1: holds | does not hold (where) | not testable here

Not proven:
- AC1: what a passing test would still allow

Lens: (five lines, in this order)
- security: ...
- honesty: ...
- portability: ...
- size: ...
- duplication: ...

Gaps:
- project: a fix in this project
- kit: a residual with its generic wording

Checklist:
- one answer per question of `config/review-checklist.md`, with evidence or `n/a`

## Findings

1. (path and rule)

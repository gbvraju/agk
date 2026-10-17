# Product report, live run 1 (SPEC-0011 rules 15, 16 and 21)

Date: 2026-10-17 (from `date -u`). Kit 0.16.0 on `main` at `8cb925c` (the merge of ADR-0030). The workflow
`.github/workflows/product-report.yml` was started once by hand (`workflow_dispatch`, input `today` = `2026-10-17`) on `main`.

## Record

- **Run:** `product-report` run 1, event `workflow_dispatch`, head `8cb925c29c152723d52b2a801607a8cca65a3717`, conclusion `success`
  (about one and a half minutes from queue to the issue). Run id 39066456024.
- **Issue:** number **68**, title `agk product report 2026-W41`, label `agk-product-report` (the label did not exist; the workflow
  created it, description `Weekly product report`), created by `github-actions[bot]`, state open. It is the only issue with that label.
- **Week covered:** 2026-W41, Monday 2026-10-05 to Sunday 2026-10-11 (UTC), the full ISO week before the week of `today`.
  The lists of what waits are as of 2026-10-17.
- **The five headings, as they appear in the issue body, in order:**

  ```
  ## Delivered
  ## Proven
  ## Needs you
  ## At risk
  ## Cost
  ```

- **First line of the body:** `<!-- agk-product-report: 2026-W41 -->`.
- **Footer:** `facts: 8cb925c29c152723d52b2a801607a8cca65a3717`, `metrics: #39 "agk metrics 2026-W41"`, `drift audit: none found`. No
  `dirty` notice (the checkout is clean).

## What the sections held (read from the issue)

- *Delivered:* REQ-001 and REQ-003 (`done`), with their criteria. No pull request was merged in W41, so no `merged` line.
- *Proven:* REQ-002 `is proven (last change PR #67: proven)`; REQ-001 and REQ-003 `is not proven: the last change (PR #60) was not
  shown to need its test`; and `17 requirements are planned and not counted here`.
- *Needs you:* one group, `Planned requirements with no spec (5)` (REQ-004 to REQ-008). No Draft spec, Proposed ADR, waiting
  question, pull request without a verdict or overdue residual at the time.
- *At risk:* `drift audit: 0 findings (D1 0, D2 0, D3 0, D4 0, D5 0, D6 0, D7 0); no open drift issue`.
- *Cost:* `nothing this week`.

## Findings

- The report is a function of the facts at `8cb925c`; the footer names that commit, so the issue can be reproduced with `facts.py` at
  that commit and `product_report.py --facts` on it (SPEC-0011 rule 21). This record does not re-run it.
- Dispatching on a Saturday with `today` set to that day covers W41, which holds none of this week's merges (PRs #66 and #67 merged on
  2026-10-17, in W42). The first scheduled run, Monday 2026-10-19 07:13 UTC, covers W42 and creates its own issue
  `agk product report 2026-W42`; it does not touch #68.
- *Proven* reports REQ-001 and REQ-003 as not proven because their last change (PR #60) read `not-proven` in the proof job, which was
  the first real run of that check (`docs/runs/proof-checks-live-1.md`). That is what the facts hold; the report does not judge it.
- `(verify)`: whether GitHub keeps the scheduled run enabled after 60 days without repository activity (SPEC-0011 residual); the
  doctor's `drift-workflow-state` now reports this workflow too.

## Maintainers' ruling (2026-10-18)

REQ-001 and REQ-003 read `not-proven` because the proof job of PR #60 ran without pytest (`red-on-head`, an environment fault fixed by
PR #61 and PR #63), not because their behaviour is unproven. This is a known false flag for criterion c. It is resolved when the next
change to either requirement reads `proven`, and is tracked as a residual (due 2026-10-31). A second residual asks that the Proven
line print the proof reason next to `not-proven` (for example `red-on-head`), due 2026-11-15. Both are in `docs/runs/residuals.md`.

## Not done here

The pilot upgrade (`docs/runs/pilot-upgrade-brief.md`) and the two weeks of product-owner answers (criterion a) are the maintainers'
and the pilot session's steps. Nothing here names or reads the pilot repository.

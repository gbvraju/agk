# K5 early, live run 1 (REQ-023, REQ-024, REQ-025; SPEC-0016, SPEC-0017, SPEC-0018)

Date: 2026-10-21 (from `date -u`). Kit 0.31.0 on `main` at `4eebec7` (the merge of #105). The workflow `.github/workflows/product-report.yml` was started once by hand by the maintainers
(`workflow_dispatch`, no `today` input, so the default week) on `main`. Everything below was read from the GitHub REST API (GET) after the run; nothing was typed in. The week is the same as
that of `short-report-live-1.md` (2026-W42, issue 88), so the two bodies can be set side by side; what changed between them is the three requirements of the K5 early scope (ADR-0053).

## Record

- **Run:** `product-report` run 4, event `workflow_dispatch`, head `4eebec7a04726266e38118d828d4c9de1f95a699`, conclusion `success`. Run id **39518584432**.
- **Wall time:** run created 2026-10-21T00:00:09Z, updated 00:03:08Z: **2 min 59 s**. The one job `product-report` ran 00:00:14Z to 00:03:07Z (2 min 53 s); its step "Write the week's report to one issue"
  (the `facts.py` run, the report, the issue edit) ran 00:00:16Z to 00:03:06Z (2 min 50 s). The log prints the report's first two lines at 00:03:04Z, so `facts.py` and `product_report.py` took about 2 min 48 s.
  The checkout (full history, `fetch-depth: 0`) took 1 s.
- **Issue:** https://github.com/gbvraju/agk/issues/88, title `agk product report 2026-W42`, label `agk-product-report`, state open. The week label is that of the earlier runs, so the workflow replaced the
  body of issue 88 and did not create an issue; `updated_at` is 2026-10-21T00:03:05Z.
- **Week covered:** 2026-W42, Monday 2026-10-12 to Sunday 2026-10-18 (UTC); the lists of what waits for you are as of 2026-10-21.
- **Footer:** `facts: 4eebec7a04726266e38118d828d4c9de1f95a699`, **`kit version: 0.31.0`** directly after it, `metrics: #86 "agk metrics 2026-W42"`, `drift audit: none found`.

## Before and after (issue 88, week 2026-W42, 74 pull requests merged)

The "before" is the record of `short-report-live-1.md` (run 3, kit 0.27.0, `main` at `a974d30`, 2026-10-20), which read the body of issue 88 then; that body was replaced by this run, so the "before"
counts are that record's.

| Section | Before: lines | After: lines | What the lines are after |
| --- | --- | --- | --- |
| Delivered | 5 | **3** | REQ-001, REQ-003, then `74 pull requests were merged this week` with the link |
| At risk | 37 | **4** | the sent-back pull request, the drift line, one line of 33 pull requests merged with no verdict, one line of 2 merged before their last commit was cleared |
| Cost | 1 | 1 | the totals line alone, now ending with the estimate |

### At risk (REQ-023, SPEC-0016)

The four lines after, verbatim:

```
- PR #53 "docs: draft SPEC-0011 (decision inbox and weekly product report)" was sent back 2 times — https://github.com/gbvraju/agk/pull/53
- drift audit: 1 finding (D1 0, D2 0, D3 0, D4 0, D5 0, D6 0, D7 1); no open drift issue
- PRs [#1](https://github.com/gbvraju/agk/pull/1), [#2](https://github.com/gbvraju/agk/pull/2), [#3](https://github.com/gbvraju/agk/pull/3), [#4](https://github.com/gbvraju/agk/pull/4), [#5](https://github.com/gbvraju/agk/pull/5), [#6](https://github.com/gbvraju/agk/pull/6), [#7](https://github.com/gbvraju/agk/pull/7), [#8](https://github.com/gbvraju/agk/pull/8), [#9](https://github.com/gbvraju/agk/pull/9), [#10](https://github.com/gbvraju/agk/pull/10), [#11](https://github.com/gbvraju/agk/pull/11), [#12](https://github.com/gbvraju/agk/pull/12), [#13](https://github.com/gbvraju/agk/pull/13), [#14](https://github.com/gbvraju/agk/pull/14), [#15](https://github.com/gbvraju/agk/pull/15), [#16](https://github.com/gbvraju/agk/pull/16), [#17](https://github.com/gbvraju/agk/pull/17), [#18](https://github.com/gbvraju/agk/pull/18), [#19](https://github.com/gbvraju/agk/pull/19), [#20](https://github.com/gbvraju/agk/pull/20), [#21](https://github.com/gbvraju/agk/pull/21), [#22](https://github.com/gbvraju/agk/pull/22), [#23](https://github.com/gbvraju/agk/pull/23), [#24](https://github.com/gbvraju/agk/pull/24), [#25](https://github.com/gbvraju/agk/pull/25), [#26](https://github.com/gbvraju/agk/pull/26), [#27](https://github.com/gbvraju/agk/pull/27), [#28](https://github.com/gbvraju/agk/pull/28), [#30](https://github.com/gbvraju/agk/pull/30), [#31](https://github.com/gbvraju/agk/pull/31), [#32](https://github.com/gbvraju/agk/pull/32), [#46](https://github.com/gbvraju/agk/pull/46) and [#79](https://github.com/gbvraju/agk/pull/79) were merged with no verdict
- PRs [#45](https://github.com/gbvraju/agk/pull/45) and [#50](https://github.com/gbvraju/agk/pull/50) were merged before their last commit was cleared
```

- 37 lines became 4. The items are unchanged: 1 sent back + 33 merged with no verdict + 2 merged before clearance = 36 pull requests, plus the drift line = 37, as before. The first grouped line names
  33 numbers in ascending order (1 to 28, 30, 31, 32, 46, 79), each its own link, no range, no title; the second names 2. The two single lines (`PR #53`, and the drift line) are as they were.
- The "before" record kept the counts (37 lines: the sent-back pull request, the drift line, and 35 merged without a verdict or before clearance) and not each line, so that the set of 35 numbers is the
  same is shown by the count (33 + 2 = 35) and by the test of SPEC-0016 rule 5, not by a line-by-line comparison with the old body.

### Delivered (REQ-024, SPEC-0017)

`done_on` of every `done` requirement, computed by `facts.py` on a checkout of `4eebec7` with its full history (the same function the workflow ran, run again outside it):

| Requirement | `done_on` | In W42 (2026-10-12 to 2026-10-18)? | Listed |
| --- | --- | --- | --- |
| REQ-001 | 2026-10-14 | yes | yes |
| REQ-003 | 2026-10-14 | yes | yes |
| REQ-021 | 2026-10-20 | no (W43) | no |
| REQ-022 | 2026-10-20 | no (W43) | no |
| REQ-023 | 2026-10-20 | no (W43) | no |
| REQ-024 | 2026-10-20 | no (W43) | no |
| REQ-025 | 2026-10-20 | no (W43) | no |

- Before, Delivered listed four done requirements (REQ-001, REQ-003, REQ-021, REQ-022) and the pull request line; after, it lists the two that became done in W42. REQ-021 and REQ-022 were done on
  2026-10-20, so they belong to the next report (W43). None of the seven read `unknown`: the workflow's checkout has the history, so no `(week it became done: unknown)` note appears.

### Cost (REQ-025, SPEC-0018)

The totals line, verbatim:

```
- This week: 74 pull requests merged; hours in total: 130.0; fix verdicts in total: 32; declared "Behaviour: unchanged": 4; estimate: none declared this week — https://github.com/gbvraju/agk/pulls?q=is%3Apr+is%3Amerged+merged%3A2026-10-12..2026-10-18
```

The text before the new ending is the same as before (74, 130.0, 32, 4). `estimate: none declared this week` is right and not a measurement: none of the 74 pull requests of W42 carries `Size:` and `Expected:`
(they were merged before the brief templates had them). The within-range count has not yet been shown on real data; the first pull request whose body carries the two lines will show it.

## The residual of ADR-0059 (the extra GET per pull request)

- **What the log shows:** only times. The step prints the report's first lines and the issue URL; it prints no count of API calls, so the number of `pulls/{n}/commits` requests is not in the log.
- **Run time:** 2 min 59 s for run 4 (kit 0.31.0) against 2 min 26 s for run 3 (kit 0.27.0, 2026-10-20T08:12:13Z to 08:14:39Z): 33 s more. That is not the cost of the commits GET alone. Between the two runs
  the window gained the pull requests merged since (the K5 early scope and the lean install, #95 to #105), each with its own files, comments and runs reads, and `done_dates` reads the history (0.15 s
  locally). The two runs cannot be split into those parts from what the log holds.
- **Not measured, and why:** an API-call count needs a count in the workflow or in `facts.py`; neither prints one. It is recorded as a finding below, not built here.

## Findings (not fixed here)

1. **The footer's `drift audit: none found` reads against At risk's `drift audit: 1 finding (...); no open drift issue`.** The footer line names the open drift *issue* (none), the At risk line counts the
   *findings* (one: D7, `tests/kit/test_review_report.py:109`). A reader sees "none found" and "1 finding" in one report. The footer wording is a candidate for a later change; both lines are correct as specified.
2. **Proven attributes `last change PR #105` to REQ-001, REQ-002, REQ-021 and REQ-022, although #105 advanced REQ-025.** The "last change" is the latest merged pull request that touched a file holding
   a test marker of the requirement. For REQ-002, REQ-021 and REQ-022 that file is `tests/kit/test_product_report.py`, a shared test file that #105 edited. For REQ-001 it is a false marker: the marker scan
   (`find_ac_markers`) takes any `REQ-nnn` text in a test file as a marker with no criterion (`ac` null), and the new tests of #105 hold the sample body `"Advances: REQ-001\n"` as a string
   (`tests/kit/test_estimate.py` lines 50, 65 and 118; `tests/kit/test_facts_estimate.py` line 67). So a string in a test can move the "last change" of a requirement it does not test. The line is true to
   its rule and reads wrong to a person; carrying the `Advances:` line of the pull request in the facts, and reading a marker only where it names a criterion, would give a better attribution.
3. **The release tag `V0.30.0` is written with a capital V** (the checkout log fetches `V0.30.0` beside `v0.28.0`, `v0.29.0` and `v0.31.0`). SPEC-0005 rule 14 pins an install by the `ref` `v<kit_version>`, so a
   team that pins `v0.30.0` finds no such tag. The tag is the maintainers' to rename or add.
4. **`actions/checkout` is pinned to a Node 20 release** (`11d5960a3267...`, v4.4.0): the job log warns "Node.js 20 is deprecated ... forced to run on Node.js 24". The workflow is a kit file that every
   project installs; moving the pin is a kit change (the pin test requires a full commit SHA).
5. **The run time and the number of API calls of `facts.py` are not measured** (above). Printing a count of GET requests in `facts.py`'s error output, or timing the step, would let the residual of ADR-0059
   be closed from a log.

## What this shows, and what it does not

- It shows the three K5 early requirements working on a real report: a week with 36 pull requests at risk is four lines with every number named, Delivered lists what became done in the week and no
  more, and the Cost line carries the estimate ending.
- It does not show that a reader finds the grouped form better, or that the estimate ending says anything yet: no pull request has declared an estimate, and nobody outside the project has read the report.

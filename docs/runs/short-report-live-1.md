# Short report, live run 1 (REQ-022, SPEC-0015; REQ-021, SPEC-0014)

Date: 2026-10-20 (from `date -u`). Kit 0.27.0 on `main` at `a974d30` (the merge of #94). The workflow `.github/workflows/product-report.yml` was started once by hand by the
maintainers (`workflow_dispatch`, input `today` = `2026-10-19`) on `main`. Everything below was read from the GitHub REST API (GET) after the run; nothing was typed in.

## Record

- **Run:** `product-report` run 3, event `workflow_dispatch`, head `a974d30d6c8a048d82164330211095791fba810e`, conclusion `success`, 2026-10-20T08:12:13Z to 08:14:39Z. Run id 39391701430.
- **Issue:** number **88**, title `agk product report 2026-W42`, label `agk-product-report`, state open. The week label is the same as that of the first scheduled report (run 2, 2026-10-19), so
  the workflow replaced the body of issue 88 and did not create an issue (SPEC-0011: created, or its body replaced); `updated_at` is 2026-10-20T08:14:36Z.
- **Week covered:** 2026-W42, Monday 2026-10-12 to Sunday 2026-10-18 (UTC); the lists of what waits are as of 2026-10-19.
- **Footer:** `facts: a974d30d6c8a048d82164330211095791fba810e`, **`kit version: 0.27.0`** directly after it, `metrics: #86 "agk metrics 2026-W42"`, `drift audit: none found`.
  `0.27.0` is the `version` of this repository's `agk.toml` and the `kit_version` of `kit/manifest.json` (ADR-0050 decision 7; Q-K4-201).

## Before and after (issue 88, week 2026-W42, 74 pull requests merged)

The "before" is the body of issue 88 as the first scheduled run wrote it (run 2, kit 0.24.0, facts `4d6a72e`), read on 2026-10-19. That body no longer exists in the issue (it was replaced),
so the counts below are from that read; its own totals line, `This week: 74 pull requests merged`, agrees with the count of pull request lines.

| Section | Before: lines | After: lines | What the lines are after |
| --- | --- | --- | --- |
| Delivered | 76 | **5** | the four done requirements (REQ-001, REQ-003, REQ-021, REQ-022), then `74 pull requests were merged this week` with the link |
| Cost | 75 | **1** | the totals line alone, `This week: 74 pull requests merged; hours in total: 130.0; fix verdicts in total: 32; declared "Behaviour: unchanged": 4`, ending with the same link |
| At risk | 37 | 37 | unchanged: every pull request that was named is still named |

Before, Delivered held the two done requirements of that time and 74 lines `PR #n "<title>" was merged on <day>`; Cost held 74 lines of hours and fix verdicts and the totals line.
The after body is 79 lines and 6,509 characters in all.

- **The link** in both sections is `https://github.com/gbvraju/agk/pulls?q=is%3Apr+is%3Amerged+merged%3A2026-10-12..2026-10-18`: the repository and the opening line's two dates, read in UTC
  (the search was checked by the maintainers, Q-S0015-1).
- **The totals line** has the same text as before (74, 130.0, 32, 4); only its link changed, from all merged pull requests to the week's.
- **At risk** is the same 37 lines as before: the sent-back pull request, the drift line, and the pull requests merged with no verdict or before their last commit was cleared. REQ-022 AC5 holds on real data.
- **Needs you** and **Proven** differ from the first report only because the repository changed in between (SPEC-0014 and SPEC-0015 approved, ADR-0045 and ADR-0049 accepted, Q-S0014-1 and Q-S0015-1 ruled,
  REQ-021 and REQ-022 done), not because of the short form.

## What this shows, and what it does not

- It shows both reports of the first full cycle on this repository working on a real busy week: the footer names the kit version, and a week of 74 pull requests is read in five lines of Delivered and
  one of Cost.
- It does not show that a reader finds the short form better; nobody outside the project has read it yet. The per-pull-request hours and fix verdicts of the week are not in the report any more; they are in
  the week's metrics issue (#86) and behind the link (the residual of SPEC-0015).

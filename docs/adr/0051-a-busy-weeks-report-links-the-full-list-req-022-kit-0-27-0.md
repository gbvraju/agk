# ADR-0051: a busy week's report links the full list of merged pull requests (REQ-022, SPEC-0015), kit 0.27.0

- Status: Proposed
- Date: 2026-10-20
- Deciders: maintainers
- Related: ADR-0049, ADR-0050, ADR-0029
- Requirements: REQ-022

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

PR D of the first full cycle on AGK itself (the maintainers' brief of 2026-10-19). REQ-022 was taken in by intake (ADR-0049) and SPEC-0015 was Approved with its open question ruled (the search link reads
dates in UTC). In a busy week the report was unreadable: issue 88 had 74 one-line pull requests under Delivered and again under Cost. This ADR builds the short form tests first: the tests for AC1 to AC5 were
written and shown failing on `main` before any code (10 failed, 148 passed; the output is in the pull request body).

## Decision

1. **The threshold** (SPEC-0015 rule 1): `BUSY_WEEK = 10`, one named constant in `product_report.py`, not a setting, not read from `agk.toml` or the facts. A week is busy when more than ten pull requests merged in
   it, counted as `merged_in_week` selects them. Ten or fewer is a quiet week.
2. **Delivered** (rule 3): in a busy week every done requirement is still listed, as today; the per-pull-request lines are replaced by one line `<N> pull requests were merged this week` ending with the week link.
3. **Cost** (rule 4): in a busy week there is no line for a single pull request; the totals line keeps its text exactly as today and ends with the week link instead of the link to all merged pull requests.
4. **The week link** (rule 5): `<repo URL>/pulls?q=is%3Apr+is%3Amerged+merged%3A<Monday>..<Sunday>`, the dates of the report's opening line, built by `Links.merged_in` from `repo` and the week's two dates only.
   The maintainers verified on a real search that `merged:` reads the dates in UTC (Q-S0015-1).
5. **Nothing else changes** (rule 6): Proven, Needs you, At risk, the footer and the inbox output are unchanged; a quiet week's report is byte-identical (every existing golden is untouched). Unknown pull
   requests keep today's unknown line (rule 8). The renderer still reads only the facts file and its imports are unchanged (rule 7).
6. **Tests and fixture** (`tests/kit/test_product_report.py`, installed): a busy fixture `report/busy/facts.json` with twelve pull requests merged in the week (one sent back twice, one with no verdict, one
   declaring `Behaviour: unchanged`) and its goldens; the threshold constant; Delivered and Cost of the busy week; the link for two weeks; ten, nine, four and one pull request unchanged and eleven collapsed;
   Proven, Needs you, At risk and the footer equal to what the same facts give with the threshold lifted, and the pull requests At risk still named; the busy inbox unchanged; unknown pull requests.
7. **Kit 0.27.0**: manifest (the three new fixture files), hashes, plugin version, and `version` in this repository's `agk.toml` (ADR-0050 decision 7).
8. **Docs**: one sentence in the product-owner guide says what a busy week looks like.

## Consequences

- A busy week's report fits on a screen: the requirements, the count with one link, and the totals with the same link. The hours and fix verdicts of each pull request are no longer in the report in a busy week;
  they stay in that week's metrics issue and behind the link (the residual of SPEC-0015).
- The first weekly report of a busy week after this is merged shows the short form.

## Questions

none

## Residual

none

# Metrics: run 1 (first `workflow_dispatch`)

Date: 2026-10-15 (from `date -u`). Recorded after the maintainers ran the command of `docs/runs/metrics-first-run.md`
and told the agent it succeeded. Facts below were read with GET on `gbvraju/agk`; the agent ran nothing that writes.

## The run

| Item | Value |
| --- | --- |
| Workflow | `.github/workflows/metrics.yml` on `main` at `c815150` |
| Run | 38784232965, `workflow_dispatch`, run number 1, actor `gbvraju` |
| Started / finished | 2026-10-15 18:16:19Z / 18:16:32Z, conclusion `success` |
| Command | `gh workflow run metrics.yml --ref main -f today=2026-10-15` |
| Issue | #39 `agk metrics 2026-W41`, label `agk-metrics`, author `github-actions[bot]`, created 18:16:28Z |
| Window | 2026-10-05 to 2026-10-12 (ISO week 2026-W41, half-open) |
| Body | `closed in window: 0; recorded: 0; unknown cells: 0`; last line `<!-- agk-metrics 2026-W41 -->` |

The week is empty because every pull request of this repository closed on 2026-10-14 or later. An empty week is written
(SPEC-0007 rule 14), so the issue is the evidence that the run happened. The title, label, marker and counts are the ones
the first-run record predicted. This run was started by hand, so it does not count towards the two consecutive scheduled
weeks of criterion d (SPEC-0007 rule 24).

## What run 1 did not exercise

With zero pull requests in the window, the live reads of `comments`, `files`, `commits`, `check-runs` and `actions/jobs`
did not run in Actions. To check them before the first scheduled run, the agent ran the script locally, read-only, for the
next window: `python3 scripts/agk/metrics.py --today 2026-10-19 --repo gbvraju/agk` (window 2026-10-12 to 2026-10-19,
2026-W42; exit 0, nothing written).

| Result | Value |
| --- | --- |
| `closed in window` / `recorded` | 38 / 38 (PR #1 to #38, as of this run) |
| unknown cells | 98 |
| totals line | `rejected=1 blocked_weakenings=0 deviations=10 cost S=0 M=6 L=1 unknown=31` |
| Closed unmerged | #29: `rejected` yes, `cost_class` L |
| Verdict-derived | #33 to #37: one `Verdict: fix list`, a `Verdict: cleared` naming the merged head: `review_rounds` 1, `merged_head_cleared` yes, cost class M |
| Single `Governance checks` step | #32 (merged before the split): `blocked_weakenings` unknown, `governance_failures` 2 |

The live path works end to end on real data. The first scheduled run is Monday 2026-10-19 06:43 UTC; its issue will carry
every pull request closed from 2026-10-12 to 2026-10-19 (the 38 above and any later one).

## Observations for the maintainers

1. **#38 reads `merged_head_cleared` no.** The cleared line named `36e9df9`; the maintainers then ordered a final commit
   (`2ec8b42`, ADR-0016 Accepted), so the merged head is not the commit that was cleared. By SPEC-0007 rule 8 the field is
   `no` for every pull request that gets a final commit after its `Verdict: cleared` line. If the field is meant to show
   that nothing unreviewed was merged, a second `Verdict: cleared <final sha>` after the final commit would make it
   `yes`; the spec as Approved does not say. Raised as Q-K3-70.
2. **Old pull requests are mostly unknown.** `review_rounds`, `merged_head_cleared` and `cost_class` are unknown for #1 to
   #32 because no verdict lines exist before #33 (rule 10): 31 of the 38 cost classes. This is expected and not a defect.
3. **Static test counts move with merge order.** `tests_before` of #37 is 435 and of #38 is 386 because #37 merged after #38
   and each count is taken at the parent of its own merge commit (SPEC-0007 rule 8, amendment 1).
4. **Criterion d.** Two scheduled runs on consecutive Mondays are needed: 2026-10-19 (W42) and 2026-10-26 (W43). Record the two
   issue numbers in `docs/runs/` after the second.

## Questions

- **Q-K3-70.** Should a `Verdict: cleared <sha>` after a maintainers' ordered final commit be the convention, so that
  `merged_head_cleared` is `yes` for pull requests that receive a final commit? Draft answer: keep SPEC-0007 as it is and
  state the reading above in the notes; the maintainers decide.

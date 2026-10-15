# Metrics: the first run (for the maintainers; not run by the agent)

Date: 2026-10-15 (from `date -u`). SPEC-0007 rule 24, ADR-0016. After the pull request that adds
`.github/workflows/metrics.yml` is merged, the workflow exists on the default branch and its schedule starts. To start the
two weeks of criterion d without waiting for a Monday, run it once by hand.

## The command

```
gh workflow run metrics.yml --ref main -f today=2026-10-15
```

`today=2026-10-15` is a Thursday, so the window is the ISO week before it: Monday 2026-10-05 00:00 UTC to Monday 2026-10-12
00:00 UTC (half-open). The expected issue title is `agk metrics 2026-W41`, labelled `agk-metrics`, created by the
workflow (author `github-actions[bot]`). Its first line is `agk metrics 2026-W41 (window 2026-10-05 to 2026-10-12)`; its
last line is `<!-- agk-metrics 2026-W41 -->`; the line before the note reads
`closed in window: N; recorded: N; unknown cells: M`, with the two N equal (otherwise the first line is `INCOMPLETE`
and the job fails).

A run with another `today` writes another week: the title is `agk metrics` plus the ISO week of the Monday seven days before
the Monday of that date's week (`today=2026-10-19` gives `2026-W42`, window 2026-10-12 to 2026-10-19).

## What the maintainers check

1. The issue exists once; running the command again updates the same issue (its body is replaced, not a second issue).
2. `closed in window` equals the count of pull requests closed in that window on the pull request list (by hand).
3. `blocked_weakenings` is `unknown` for pull requests whose head commits ran the old single `Governance checks` step, and
   a number for those after the split.
4. Criterion d needs the issues of two consecutive ISO weeks created on schedule (Mondays 06:43 UTC); a week run by hand
   does not count unless the maintainers accept it (SPEC-0007 rule 24). Record the two issue numbers in `docs/runs/`.

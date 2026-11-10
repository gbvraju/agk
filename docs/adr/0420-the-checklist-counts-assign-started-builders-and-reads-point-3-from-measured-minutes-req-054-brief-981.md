# ADR-0420: The checklist counts Assign-started builders and reads point 3 from measured minutes

- Status: Proposed
- Date: 2026-11-10
- Deciders: maintainers
- Related: ADR-0374
- Requirements: REQ-054

## Context

ADR-0374 decision 3 reads point 2 (conductor runs builders) from the conductor's own `Builders started (n)` claims, capped by the
`taken:` lines, and point 3 (test optimization) from the weekly `pr tests:` line alone. On 2026-11-10 the checklist printed
"conductor started 49 of 49 builder starts (100%)" over a day in which the co-owner started builders by hand and the conductor's
reports name refused starts, and point 3 printed `unknown` because the weekly line counted no run. A share of selected runs alone
also reads `yes` when the pull request test step takes longer than the full suite on main. Brief #981 answers how both points are
measured. The answers change ADR-0374's decisions 2 and 3 (what is saved and what each point reads), so this build has its own
ADR. It changes the protected path classes `scripts/agk/` and `tests/kit/`.

## Decision

1. Point 2: a `taken:` line of a slot `sN` on brief `#b` is the conductor's when an earlier `Assign: sN #b` line (any brief form,
   a `build (x)` included) on the open issue labelled `agk-conductor`, by a listed verdict author (`verdict_authors` of
   `config/reviewers.yaml`), is not already spent; one `Assign:` starts one take. Every other take is by hand. The measure is
   `conductor <a> of <n> (<p>%); by hand <b>; stalls replaced <s>`; `yes` needs `conductor_share` as before, `no` at 0. The
   reports' `Builders started` count is no longer read. When the authors or the conductor issue were not saved, the point is
   `unknown` with that reason.
2. Point 3: the figures are the weekly `pr tests:`, `pr tests median:` and `full suite:` lines when the `pr tests:` line counts at
   least one run; otherwise the same three lines that `metrics.py` writes, computed at save time for the pull requests closed in
   the checklist's window with the GETs `metrics.py` already makes (no new reader). `yes` needs the selected share
   (`selected_share`) and a median selected test step no longer than the median full suite on main; otherwise `partly` (an
   unknown median cannot read `yes`); `no` when no run was selected. The measure prints both medians and names its source
   (`weekly line` or `window`).
3. `metrics.py --save-checklist` also saves each comment's author login, the listed verdict authors, the numbers of the open
   `agk-conductor` issues, the weekly `pr tests median:` and `full suite:` lines, and the window figures of decision 2 (null when
   the weekly line counts a run or the pull requests cannot be listed). `checklist.py` still imports only the standard library and
   `common.py` and makes no network call.

## Consequences

Point 2 tells a hand start from a conductor start, and point 3 says whether selection made the pull request step faster than the
full suite. A save with no weekly line costs the GETs of the window's pull requests, their commits, runs, jobs and logs, as the
weekly report does. A file saved before this change has no authors or conductor issue, so point 2 reads `unknown` until the next
save.

## Residual

- 2026-12-10: An `Assign:` posted before the window's start is not saved, so a take early in the window that it started counts
  as by hand; the split is a lower bound for the conductor.
- 2026-12-10: A weekly `pr tests:` line that counts no run falls back to the window like a missing one (`Q-981-1`); the brief names
  only a missing line.

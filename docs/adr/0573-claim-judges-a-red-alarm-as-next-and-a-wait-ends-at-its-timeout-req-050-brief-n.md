# ADR-0573: A claim judges a red alarm as `next` does, and a wait ends at its timeout

- Status: Accepted
- Date: 2026-11-15
- Deciders: maintainers
- Related: brief #1368, found bug #1341, found bug #1297, brief #1052, brief #1316, SPEC-0050, plan #661
- Requirements: REQ-050

## Context

Found bug #1341: `session.py claim` let a fix brief of an open red alarm past the overlap (`red_fix`, brief #1052) but
not the alarm itself. The alarm carries `Touches: **`, so the overlap judgement found every open builder pull request
in its way and `claim` printed `skip #<alarm>: waits for pull request #<n> ...`, while `next --take` took the same
alarm. SPEC-0050 rule 4 says `claim` refuses what `next` refuses, with the same line. Measured on main at eff2fcb: the
claim of an alarm with one open builder pull request was refused (exit 1) where `next --take` took it.

Found bug #1297: `watch --pr` and `watch --assign` slept `min(pause, max(interval, left))`, so a quiet wait could end a
whole `--interval` after its `--timeout`. Measured with a fake clock: `--interval 60 --timeout 90` ended at 120 s, and
`--interval 300 --timeout 90` at 300 s, past a wrapper's `timeout`.

## Decision

1. `claim`'s gate first reads the open briefs once. When the brief claimed is an open red alarm (`is_red`), it is
   judged by the survey that `next` builds while the branch is red (`survey`, `read_gone`, `settle_takes`), never by
   the overlap: it is refused for every reason `next` skips it (taken, stale, parked, a shape problem) with `next`'s
   own line, and otherwise taken. A fix brief keeps `red_fix` as before; every other brief is judged by the overlap
   as before. A hold is still refused before the gate, as before.
2. Both waits sleep `min(pause, max(1, left))` while a timeout is set: a pause never runs past the timeout by more
   than one second (plus the read in progress), and is never under one second at the bound, so a wait never spins.
   The end lines (`timeout`, `assign-timeout`, `no event`, `renew: no event`) are unchanged.

## Consequences

A builder can claim the red alarm it is told to fix while other builder pull requests are open, and a foreground
`timeout 540 ... --timeout 520` wait ends inside its wrapper. Protected path classes changed: `scripts/agk/`
(`session.py`) and `tests/kit/` (`test_session_claim_overlap.py`, `test_session_watch_answers.py`).

## Residual

- 2026-11-15: the first read of a wait that cannot read GitHub still sleeps a whole `--interval` between its five
  tries (`watch --pr`'s baseline, `watch --assign`'s), as on main; it ends on the fifth failed read, not on the
  timeout.

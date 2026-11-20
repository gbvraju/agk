# ADR-0654: A comment or a finished run starts a job only when it can act (REQ-039)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1554, ADR-0207 (brief #369), ADR-0368 (brief #776), ADR-0373 (brief #797), ADR-0476 (brief #1116), ADR-0646 (brief #1534), brief #1539
- Requirements: REQ-039

Protected classes: `.github/workflows/`, `scripts/agk/`, `tests/kit/`

## Context

Read on main at 5a5ebf9d over 23 hours (18:30Z 2026-11-18 to 17:30Z 2026-11-19, one-hour windows so that none reached
the 1,000-run cap), the kit's repository made 4,382 workflow runs and 1,185 minutes that a private repository would bill
(1,237 a day). 2,498 of the runs were comment runs on the plan issue #661, nearly all from about 1,230 edits of the one
conductor lease comment: every `conductor.py watch` start renews the lease, and the conductor starts a new `watch` after
each event, so the comment was edited about once a minute. Each edit makes one run of `agk-route` and one of `merger`, both
skipped by their job `if:` (0 billed, but every run is listed and paged by the readers of runs).

| workflow [event] | runs | jobs started | billed min |
|---|---|---|---|
| agk-route [issue_comment] | 1,702 | 255 | 264 |
| merger [issue_comment] | 1,702 | 63 | 63 |
| agk-route [workflow_run] | 268 | 172 | 176 |
| merger [workflow_run] | 268 | 0 | 0 |
| agk-route [pull_request] | 71 | 46 | 46 |
| agk-route [push] | 71 | 15 | 16 |
| governance full [push] | 71 | 15 | 232 |
| governance full [pull_request] | 69 | 69 | 185 |
| proof [pull_request] | 69 | 44 | 46 |
| governance edited [pull_request] | 53 | 53 | 121 |
| agk-brief [issues] | 35 | 33 | 33 |
| merger [schedule] | 3 | 3 | 3 |
| **total** | **4,382** | | **1,185** |

GitHub cannot filter an `issue_comment` by its text; the job `if:` is the only filter and both comment workflows already
have one. The merger's `workflow_run` acts only on a failed merge-queue run, yet every finished governance and proof run
starts it. The merger's comment job and its scheduled `sweep-gate` start, and bill a minute, even where
`merge_cleared.py` would stop at its gate (`auto_merge` not `true`, `execution = "local"`). And the router's `if:` does
not list `Answer:`, which `route.py` already unparks on (ADR-0646 residual).

Options weighed: (A) filters on the comment's text at the trigger (GitHub has none; only `Answer:` is missing from the
existing job `if:`); (B) stop the noise where it starts: the lease writer, the merger's queue chain, a merger job that
would only read `off`, and the router's missing line; (C) move the lease and slot markers to a store that starts no
workflow (changes SPEC-0061 rule 3 and every marker reader); (D) branch filters on `push:` and cancel-in-progress for the
router.

## Decision

(B) is chosen, with the one missing line of (A). (C) is not chosen here (Q-1554-3); (D) is not chosen (Q-1554-1; the router
must finish the label it writes).

1. `conductor.py lease --take` by the name that already holds a valid lease whose own time (`Conductor: active <time>`)
   is less than `RENEW_EVERY` (240 s) old writes nothing: it prints the same `lease: taken by <name> until <time>` line
   with the lease's current end and keeps the mark file. A free, lapsed or stalled lease, one 240 s or older, and
   `--release` write as before. `LEASE_MINUTES` stays 10, so a lease left by a take has at least 6 minutes. `watch`'s
   renewal and the watchdog's take go through the same path.
2. `merger.yml`'s `workflow_run` trigger carries `branches: ['gh-readonly-queue/**']`, so only a merge-queue run starts
   it (verify the branch form against a real queue run). The job `if:` and the step `Report a removal from the merge
   queue` are unchanged. The router's `workflow_run` keeps no branch filter.
3. `agk-route.yml`'s job `if:` starts on a created comment whose first line starts `Answer:`.
4. A repository variable `AGK_MERGER` with the value `off` keeps the merger job from starting on a `Verdict:`, `Approve:`
   or edited `Final:` comment, and `sweep-gate` from starting on `schedule`. The dispatch with `pr`, a sweep by hand, the
   `status` event and the merge-queue report stay ungated. Unset or any other value reads as before. `agk-route.yml`
   passes the variable to its step, and `route.py`'s `merger_starts_itself` is false when it is `off`, so the router
   dispatches the merger once for a cleared head and no merge is lost. `doctor.py` row `merger-variable` offers the one
   command where the merger would stop at its gate anyway, and warns when `auto_merge = true` in GitHub mode and the
   variable is `off`; it never runs the command and names the setting, never a value.
5. `route.ROUTER_CREATED`, `route.ROUTER_EDITED`, `merge_cleared.MERGER_CREATED` and `merge_cleared.MERGER_EDITED` hold
   the first lines each job acts on; the tests read every `startsWith(github.event.comment.body, '<line>')` of each job
   `if:` and assert the sets equal, so a reader without its trigger, or a trigger without its reader, fails.

No spec rule changes (Q-1554-4, Q-1554-5). ADR-0207, ADR-0368, ADR-0373, ADR-0476 and ADR-0646 stand unchanged.

## Consequences

In the kit (local, every workflow enabled, `AGK_MERGER = off`) the 23-hour window replays to about 2,344 runs and 1,122
billed minutes: the lease edits fall from about 1,230 to at most 345 (15 an hour), the merger's 268 `workflow_run` runs go,
and its 63 comment jobs and its scheduled gate jobs do not start. In a customer project with the defaults
(`auto_merge = false`) the variable saves up to 96 scheduled jobs and one job per verdict a day. Projects that do not set
the variable change only by answers 1 to 3. Personal mode installs no workflow and takes no lease: no change. A
`GITHUB_TOKEN` comment still starts nothing (verify).

## Residual

- 2026-11-20: the branch form `gh-readonly-queue/<base>/pr-<n>-<sha>` is read from GitHub's documentation, not from a real
  queue run of this repository (verify before the merge).
- 2026-11-20: member and reviewer slots still renew every 240 s (SPEC-0061 rule 3), 30 skipped runs an hour per live slot
  (Q-1554-3, a follow-up Intake on the owner's word).
- 2026-11-20: the first full day after the merge is read again with the same windowed listing and reported on #1554.

# ADR-0383: A cleared pull request merges within minutes: an edited verdict counts, the sweep reads verdicts, every finished check sweeps

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: ADR-0354, ADR-0373, ADR-0263, amendment 148, brief #836
- Requirements: REQ-046

## Context

Pull request #831 was cleared at 3c24019 with its checks green and stayed open until the owner merged it from the app. The verdict comment was created at 02:23:38Z and corrected in place at 02:27:18Z; the merge was at 04:19:55Z (09:49 IST), 1 hour 56 minutes after the verdict and 1 hour 52 minutes after the edit. Three causes, each read on GitHub on 2026-11-09:

1. `merger.yml` and `agk-route.yml` start on `issue_comment` `created` only, so the edit started neither, and the label stayed `agk:fix` from 02:23:51Z.
2. `merge_cleared.py --sweep` lists only pull requests labelled `agk:ready`, so a stale label hides a cleared head.
3. The `*/15` schedule of `merger.yml` ran twice overnight (2026-11-08 20:46Z and 2026-11-09 00:38Z). GitHub runs scheduled jobs on a best-effort basis and drops them under load.

This build changes the protected path classes `.github/` (the workflows `merger.yml` and `agk-route.yml`), `scripts/agk/` and `tests/kit/`. A workflow change needs its own ADR (session rule 36), and the owner's yes for it is quoted in brief #836.

## Decision

1. `merger.yml` and `agk-route.yml` also start on `issue_comment` `edited`, for a comment whose first line starts `Verdict:`, `Final:` or `Approve:`. A created comment starts them as before. `merge_cleared.py --event` reads an edited body as it reads a new one and takes the edited `Final:` line only under `action: edited`. The router's state already comes from all comments.
2. `--sweep` lists every open, non-draft pull request, oldest first, and acts on those whose latest verdict clears the current head, by the reading of the one guarded command, at most five guarded merges a run. This replaces decision 2 of ADR-0373: the label is never an input. A cleared pull request labelled `agk:fix` or `agk:review` prints `LABEL #<n> <label> but cleared`, and when it is left unmerged the router is run for it, in process, with the job's token. A merged pull request gets its label from the router's own `closed` event.
3. In `merger.yml` the job `sweep-gate` also starts on `workflow_run` and needs the job `merger`, so the sweep runs after the event job on every finished `governance` or `proof` run. Both sweep jobs say `!cancelled()`, because a skipped ancestor skips a job unless its condition says otherwise. The job `sweep` has its own concurrency group, so that the per-pull-request groups of `workflow_run` never run two sweeps at once. The schedule and `workflow_dispatch` stay as a fallback.
4. Each `conductor.py watch` prints, after its other lines, `SWEEP late <m> min` when no `schedule`, `workflow_dispatch` or `workflow_run` run of `merger.yml` finished in the last 30 minutes (a cancelled or skipped run does not count) and a cleared, non-draft pull request is open. It reads nothing with the sweep off, and a read that fails prints nothing. The line never ends a watch by itself: it goes with the lines the watch prints anyway.
5. For each pull request the sweep merges it prints `MERGED #<n> <m> min after cleared`, counted from the verdict's last edit. `UNMERGED` counts from the same moment.

## Consequences

A cleared head waits at most until the next finished `governance` or `proof` run in the repository, and an edited verdict acts at once. Each finished run costs the short gate job and, with `auto_merge` on, one short sweep job. A project without `[flow] auto_merge = true`, or in local or personal mode, stops at the gate and opens no `merge` environment; it gets the workflow changes through the kit.

## Residual

- 2026-11-09: GitHub reports who wrote a comment, not who edited it. `judge` reads the author, so an account that may edit another's comment could turn it into a clearing verdict. That reading is not new: every run already read the edited body. This decision only starts a run sooner. A second account in `conductor_accounts` does not close it.
- 2026-11-09: a verdict that clears the head and carries a stale `agk:ci-running`, `agk:ci-red` or `agk:conflict` prints no `LABEL` line: the router gives those states before a verdict's own, so they do not disagree with it.
- 2026-11-09: the owner's words name a dispatch from the conductor's hourly pass; the brief makes it optional (answer 4) because answer 3 needs no session. Nothing dispatches a run.
- 2026-11-09: `.claude/agents/conductor.md`, which would name `SWEEP late` under `Needs a fix`, is not changed here: `.claude/` is not among the brief's `Touches:` (`Q-836-1`).

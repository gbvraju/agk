# ADR-0554: A waiting session costs no model turns

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: ADR-0362, ADR-0368, ADR-0453, ADR-0525, ADR-0553, brief #1310, brief #1287, plan #661
- Requirements: REQ-050

## Context

Brief #1310 found, on one customer project in local mode, about 250 USD of model credit in a day with a conductor and two
builders. A model turn re-sends the whole conversation, and a conversation left idle past the prompt cache's lifetime is
re-read at full price on its next turn. Turns happened with no new work in them: a builder's background `watch --pr` ended
at the runtime's background-command limit, a slot's `watch --assign` returned every 300 s (`WATCH_BOUND`) with `no event`,
the conductor's `/loop` woke every 10 minutes to run `review-queue --fingerprint` as a model turn, and the runtime's idle
recap lines are model output too. Ending a builder when its pull request opened made fix lists worse, because a fresh
session read everything again, so a builder still lives until its pull request merges or closes.

## Decision

1. `session.py watch --pr N` and `watch --assign ID` take `--until-event`. They then return only on a real event (a
   verdict, a `Correction:`, an `Answer:` or `Maintainer answer:` to the builder's `Question:`, an `Approve:` of the head,
   a `Tell:`, a change of the `agk:` label, a merge, a close, a conflict, an `Assign:`), or, with nothing, after `[flow]
   wake_minutes` (110 by default, below the runtime's 2-hour background limit `(verify)`) with the one line `renew: no
   event` (exit 0), so that the session restarts the watch at the cost of one short turn. A slot's lease is renewed by the
   script every 240 s during the wait (`watch --pr` with `--session` naming a slot that holds its run, and `watch
   --assign`), so the 300 s bound of a slot's `watch --assign` does not apply under `--until-event`; a renewal that cannot
   read GitHub ends the wait with the existing unreadable exit (4), and one that is refused prints the lease's line and its
   exit. Every event line found on one read is printed, not only the first. Without the flag nothing changes; a cloud
   scheduled task keeps its 9-minute foreground form, since its session ends when idle.
2. `session.py summary --pr N --file F` posts the pull request's one working summary: a comment whose first line is
   `Summary: <head>` (the head when it was written) followed by the file, at most `[flow] summary_lines` lines (25 by
   default); a longer file is refused with a line naming the setting. A second run edits that comment in place (one
   PATCH), never a second comment. A builder runs it when it opens and when it readies its pull request, after each fix
   list, and before any hand-over line (ADR-0453). `session.py resume --pr N` prints that summary, the newest verdict and
   the command for the diff since the summary's head; with no summary (an older pull request) it prints the newest
   `Report:` of the author and the diff since that report's head, as before.
3. `conductor.py watchdog --pass` is the scripted conductor pass for local mode. It checks the pause and the adapter as
   the watchdog does, takes or renews the conductor lease under its NAME (another live holder, an interactive conductor,
   starts nothing), and runs `review-queue --fingerprint`, the plan's `Start` line and `sweep` in the script. It starts one
   conductor job through `[flow] launch_adapter` only when the fingerprint differs from the one of the last job, the plan
   starts at least one brief, the lines `sweep` printed, without their ages and times, differ from those of the last
   job, or no job ran for 24 hours (the daily report); otherwise it prints
   `watchdog: nothing changed; no job started`. The job does one pass and ends, and leaves the lease to the script. The
   fingerprint and the time of the last job are kept in `<git dir>/agk/watchdog.json`, beside the lease mark, only after a job started without error,
   so a job that fails is tried again on the next pass. `--install --pass` prints the scheduler line every 10 minutes.
   An interactive conductor with `/loop` is unchanged.
4. Recaps are off for agent sessions: the watchdog and `launch.py` start every adapter with
   `CLAUDE_CODE_ENABLE_AWAY_SUMMARY=0` `(verify: https://code.claude.com/docs/en/env-vars, read by a helper agent of the
   builder session, not by the builder)`. A person's own session is untouched.
5. By mode: CI keeps the builders' cloud form and gains nothing else; local mode takes all of it; personal mode uses the
   same `--until-event` wait and has no conductor.

## Consequences

In the recorded double a quiet hour makes no return of `watch --until-event` before `wake_minutes` and renews a slot's
lease every 240 s, and `watchdog --pass` starts no job on an unchanged fingerprint. Protected path classes changed:
`scripts/agk/` (`session.py`, `conductor.py`, `launch.py`, `config.py` for the two new `[flow]` keys), `tests/kit/`
(`test_wait_until_event.py`, and the write count of `test_session.py`), `kit/` (`kit/templates/runtime/builder.txt`),
`config/` (`config/session-rules.md` rule 18), `.claude/` (`.claude/agents/conductor.md`) and `agk.toml` (the new test
file in the `[[testing.map]]` entries of `session.py`, `conductor.py` and `launch.py`).

## Residual

- 2026-11-15 (verify): the background-command limit (30 minutes by default, 2 hours at most, in unattended sessions) and
  the recap variable were read from the runtime's documentation by a helper agent, not confirmed on a run.

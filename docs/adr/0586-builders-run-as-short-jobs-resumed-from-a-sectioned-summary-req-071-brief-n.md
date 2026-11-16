# ADR-0586: Builders run as short jobs, resumed from a sectioned summary, started on events and held after two failures

- Status: Accepted
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1389, SPEC-0064 rules 4, 9, 15 and 16 (c), Q-S0064-1, brief #1387 (ADR-0585), brief #1355 (ADR-0568), brief #1310 (ADR-0554), brief #1386, plan #661
- Requirements: REQ-071

## Context

SPEC-0064 (Approved) makes every AI session a short job that ends. Today a builder lives for its pull request:
`kit/templates/runtime/builder.txt` (LIFETIME) and session rule 10 keep it waiting in `session.py watch`, and the
watchdog's builder pass (ADR-0568) restarts any builder whose process ended, whatever it waits on. The working summary
of ADR-0554 is free text, so a job that resumes from it may find no decision, risk or test command in it
(`Q-S0064-1` was ruled with two conditions: fixed sections, refused when one is missing, and the fix-list rounds
measured before and after this build). Nothing stops a job that fails on every start from being started again each
hour.

## Decision

1. **The next job starts on its event (rule 4).** In `watchdog` and `watchdog --pass`, an ended builder with an open
   pull request is `left (waits for an event)`, and no session is open, until one of: a `Verdict:`, `Correction:`,
   `Answer:` or `Maintainer answer:` newer than its own newest move, an `agk:conflict` or `agk:ci-red` label, or a
   first failure of its last job. Then one job starts through the adapter as before, with the job kind `fix` and the
   pull request as its item (brief #1386's record fields), and `launch.FIX_JOB` added to the resume prompt: resume
   from the summary, the newest verdict and the diff, do the one step, push, refresh the summary, post the `Report:`
   and end, never run `session.py watch`. A builder with no pull request, an idle one, a parked or handed-over one and
   #1355's signs of work (a fresh `lock.py` heartbeat among them) are as ADR-0568 decided, and one restart per hour
   still holds.
2. **The back-off (rule 9).** The supervisor keeps, in `<git dir>/agk/builders.json` (`jobs`), what each job it
   started is measured against: the head, the mark of progress (the head, the newest `Progress:`, `Report:` or
   `Question:` and the summary comment's last edit) and the newest owed line. At the job's end, counted once, a job
   that exits with a code other than 0 or leaves the mark unchanged is a failure, and a job with progress clears the
   count. Two in a row are `held (failed twice)`: the builder line says so, `sweep` prints `NEEDS-YOU: builder <name>
   #<brief> held (failed twice)`, which `agk status` shows under `held:`, and no job starts until the head changes or a
   newer owed line (a listed author's comment) is there. `agk autopilot retry <n>` is build (d)'s.
3. **The summary's fixed sections (Q-S0064-1 as ruled).** `session.py summary --pr N --file FILE` refuses a file with
   no line that starts with one of `Decisions and why:`, `Alternatives rejected:`, `Risks:`, `How to run the tests:`
   and `Where it is stuck:`, naming the first missing section and posting nothing (exit 1). Five lines fit
   `[flow] summary_lines` (25 by default). A job ends only after its summary is accepted.
4. **The texts (rule 15).** Session rule 10: a builder the supervisor starts is a short job that never runs `watch`;
   any other session keeps the wait. Session rule 18: a short job ends at its `Report:`; the steps after a merge are
   for a session that waits for it. `builder.txt` gains SHORT JOBS (where a supervisor runs and started the job) and
   names the five sections; a cloud scheduled task keeps LIFETIME until build (f). No rule line is added; the words of
   `config/session-rules.md` rise from 3436 to 3488 in `config/rule-budget.txt`, as ADR-0585 raised the steward's,
   because the wait's own sentences are checked word for word by `tests/kit/test_session_rules.py`.
5. **Measured and reversible.** The fix-list rounds per merged pull request before this build are in the pull
   request body (the last 30 merged); the after figure is read the same way once 30 pull requests have merged under
   short jobs. When it rises, one session may continue across a fix list, recorded in a follow-up brief.

Protected path classes changed: `scripts/agk/` (`conductor.py`, `launch.py`, `session.py`), `config/`
(`session-rules.md`, `rule-budget.txt`), `kit/` (`templates/runtime/builder.txt`), `tests/kit/` (`test_autopilot_build_jobs.py` and the
tests of the changed summary and restart), `agk.toml` (the `[[testing.map]]` entries), `docs/adr/` (this file) and
`changelog.d/` (one fragment).

## Consequences

A builder whose pull request waits on a review or the owner holds no session and no memory; a fix list starts one
job at the next pass. A job that cannot make progress costs at most two starts before a person is asked. A summary
written before this build is still read by `resume`; only a new one must carry the sections.

## Residual

- 2026-11-16: the first start of a builder (a new brief) stays the conductor's re-plan through `launch.py prompts`
  (`.claude/agents/conductor.md`, not in this brief's Touches), Q-1389-1 (due 2027-03-31).
- 2026-11-16: an `agk:ci-red` or `agk:conflict` label that stays after the job's push starts one more job, which ends
  with no progress and counts toward the hold (due 2027-03-31).
- 2026-11-16: the after figure of the fix-list rounds needs 30 merged pull requests built as short jobs, Q-1389-2
  (due 2027-03-31).

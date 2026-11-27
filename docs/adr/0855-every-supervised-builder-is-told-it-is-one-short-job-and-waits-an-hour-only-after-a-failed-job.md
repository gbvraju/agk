# ADR-0855: Every supervised builder is told it is one short job, and waits an hour only after a failed job

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2057, 2026-11-27T19:12:29Z)
- Related: SPEC-0064 rules 2, 4 and 9, ADR-0586, ADR-0584, ADR-0568, ADR-0190, brief #2057, brief #1389, brief #1391, plan #661
- Requirements: REQ-071

Protected classes: `scripts/agk/`, `.claude/`, `config/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0064 rule 4 makes every AI session a short job that ends. ADR-0586 built that for the watchdog's fix job only: its
resume prompt gains `launch.FIX_JOB`. A build start through `launch.start_with` (the conductor's re-plan, `autopilot.py
next`) sends `launch.PROMPT`, which ends `run session.py after and do what it says`, and session rule 10 sends any
session not started by `conductor.py watchdog --pass` to `session.py watch`. A start with no adapter (a cloud runtime)
carries no `AGK_JOB_KIND` at all. On #2037 one builder session served five `Report:` lines, its cache read rising from
16.0M to 23.0M tokens. ADR-0586 decision 1 also kept "one restart per hour still holds", so a second fix list 28
minutes after a first job that made progress waits 32 minutes more (`builder_action` returns `held (restarted within
the hour)` before anything else).

## Decision

1. **Every adapter start says it.** `launch.BUILD_JOB` stands beside `FIX_JOB`. `launch.start_with` adds the line of
   the start's job kind (`build` or `fix`) to its prompt once, through `launch.with_job`, so the conductor's re-plan,
   `prompts --resume --adapter`, `autopilot.py next` and the watchdog all send it. A prompt that already holds the line
   is left as it is; `autopilot.py next` adds it itself before `PERSONAL_NOTE`. `AGK_JOB_KIND` stays as ADR-0584 set
   it. `prompt_for` and `resume_for` alone are unchanged: a printed prompt a person pastes keeps `watch`.
2. **A start with no adapter.** `launch.py prompts --plan F --job` (and `--resume --job`) prints each prompt with its
   job line and, first, `Job: <kind> #<item> (AGK_JOB_KIND <kind>, AGK_ITEM #<item>)`: a running session with a pull
   request is a `fix` job of it, any other a `build` job of its brief. `--job` with `--adapter` is refused with the
   usage line naming `--job` (exit 2). The conductor guard allows the one word `--job` after `--plan <scratch file>`
   and nothing else; `.claude/agents/conductor.md` says a builder started by other means takes that text. Session rule
   10 reads "A builder a supervisor (`conductor.py watchdog --pass`) or conductor starts is a short job", its words
   unchanged.
3. **The hour after a failed job only (rule 9 as the back-off, rule 2 for the next job).** `conductor.gap_holds` is the
   one reader of a builder's `RESTART_GAP`. In `watch_builders` the end of the last job is counted before the action is
   chosen; for an ended builder with a pull request the hour holds only when that job counted a failure, or when there
   is no job record (an older builder). After a job with progress the next job starts in the pass its event appears.
   `held (failed twice)` stays `job_gate`'s. An idle builder, one without a pull request, the steward's start and the
   conductor's own stop keep the hour unchanged. This narrows ADR-0586 decision 1's last sentence.
4. **The class stays closed.** A test lists every function in `scripts/agk/` that calls `start_with` and every reader
   of `RESTART_GAP`; a new start or a new reader of the hour fails it until it is named.

Protected path classes changed: `scripts/agk/` (`launch.py`, `conductor.py`, `autopilot.py`), `.claude/`
(`hooks/conductor_guard.py`, `agents/conductor.md`), `config/` (`session-rules.md`, `rule-budget.txt`), `tests/kit/`
(`test_short_jobs_everywhere.py`, `test_session_rules.py`), `agk.toml` (the `[[testing.map]]` entries), `docs/adr/` (this
file) and `changelog.d/` (one fragment).

## Consequences

A builder that the conductor or a supervisor starts ends at its `Report:`, and each fix round pays its own context
rather than the whole history. A second fix round starts in the pass its verdict appears. A job that fails still waits
the hour, and two failures are still held.

## Residual

- 2026-11-27: whether a cloud conductor may start builders at all, and through which runtime tool (verify), is the
  owner's ruling; no guard for that tool is added here, Q-2057-2 (due 2027-03-31).
- 2026-11-27: the signal of use (the share of fix-round `Report:` lines from a separate job, and builder tokens per pull
  request against #2037's 23262269) is read over the next 10 merged builder pull requests (due 2027-03-31).

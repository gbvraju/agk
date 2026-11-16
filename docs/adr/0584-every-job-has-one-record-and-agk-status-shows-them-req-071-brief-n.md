# ADR-0584: Every job has one record and one log, and `agk status` shows them

- Status: Accepted
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1386, SPEC-0064 rules 3, 5, 10 and 16 (a), brief #1355 (ADR-0568), brief #1310 (ADR-0554), brief #1283 (ADR-0544), plan #661
- Requirements: REQ-071

## Context

SPEC-0064 (Approved) makes every AI session a short job that a supervisor per machine starts and stops. Build (a)
gives each job one record and one log (rule 3), one status command (rule 5) and a week of health figures (rule 10).
Brief #1355 already writes `<worktree>/.agk-session-pid` (`session=`, `pid=`, `started_utc=`, `brief=`) from both
adapters and refuses a second session of a name whose record shows a live process; a session is still known by its
name, and nothing shows what runs, what waits on the owner or why nothing starts.

## Decision

1. **The job record.** `launch.py` hands each adapter call `AGK_JOB_KIND` (`build` for a start, `fix` for a resume
   of a pull request, `build` for a resume without one, `steward` or `conductor` for `launch.py role`), `AGK_ITEM`
   (`#<brief or pull request>`; GitHub numbers issues and pull requests in one series) and `AGK_HEAD` (empty until a
   supervisor knows it). Both adapters add `kind=`, `item=` and `head=` to the record; the Windows adapter passes them
   to its tab through a `job.txt` in the session's temp folder, as it does the prompt. `read_record` reads them and
   gives `None` for a field absent or not of its form, so a #1355 record stays a record. `review` is a known kind
   that no start writes yet (build (b) starts reviews). The log `<worktree>/.agk-session.log` is in both adapters'
   exclude list. The refusal of a live name is #1355's, unchanged.
2. **`agk status`.** The new installed script `scripts/agk/autopilot.py status` lists the running jobs of this
   machine (kind, item, head, since, last event: the newer of the record and the log), each `claude` process outside
   every recorded job's process tree as `unrecorded: process <pid> (not adopted)` (a process with `--agent steward`,
   a person's own steward, is not reported), and from the plan and the sweep (the two of the three reads of one
   `watchdog --pass`) the queue, the `NEEDS-YOU:` lines as the owner's waits, those that say `held (` as the held
   jobs, and one `quiet:` line: the plan's `Start 0:` reason, or `paused (setting: paused)`. It posts nothing.
3. **The health file.** `autopilot.append_health` appends one line per pass to `agk-autopilot.jsonl` in the
   temp folder: the time, jobs started by kind, ended, failed, held, merged and the seconds from each event to its
   job's start; any other field or value is refused. The supervisor's pass that calls it is build (b)'s.
   `status --week` sums the last seven days and divides this clone's tokens of the week (`metrics.py --cost`'s local
   records) by the merged count; a figure it cannot read is `unknown`.

Protected path classes changed: `scripts/agk/` (`launch.py`, `autopilot.py`), `kit/` (`templates/start-session-local.sh`,
`templates/start-session-windows.ps1`, `manifest.json`), `tests/kit/` (`test_autopilot_status.py`), `agk.toml` (one
`[[testing.map]]` entry), `docs/adr/` (this file) and `changelog.d/` (one fragment).

## Consequences

A job is known by its record's kind and item, not its name alone, and one command shows what the machine runs and why
it is quiet, at no more GitHub reads than one pass. Until build (b) the health file has no writer, so `--week` prints
zeros of the file and `unknown` figures.

## Residual

- 2026-11-16: the unrecorded-process scan reads `ps` on Linux and macOS only; on Windows it prints `unknown`
  (verify: a Windows process table with command lines) (due 2027-03-31).
- 2026-11-16: `head=` stays empty until build (b) or (c) starts a job on a known head (due 2027-03-31).

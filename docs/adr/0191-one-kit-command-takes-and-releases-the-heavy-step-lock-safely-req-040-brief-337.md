# ADR-0191: one kit command takes and releases the heavy-step lock safely (REQ-040, brief 337)

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0182, ADR-0186
- Requirements: REQ-040

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/`, `config/`

## Context

Brief #337 (priority 1). In a pilot, several builders on one 16 GB laptop ran the full test suite at once and the machine killed
processes; the team made a lock folder by hand. The local-mode guide (#322, ADR-0182) shows a shell snippet whose `trap` releases
the lock only when one shell ends, which fails when an agent runs the lines as separate commands. The brief names no `Measured:`
line. The tests were written first (`tests/kit/test_lock.py`: collection fails without `scripts/agk/lock.py`, 0 of 19 run, at the
first checkpoint of the pull request).

## Decision

1. **`scripts/agk/lock.py run --name NAME [--session ID] [--timeout S] -- COMMAND [ARG...]` (answer 1).** Standard library
   only, no network. The lock is a folder `agk-lock-NAME` that holds `owner.json` (`session`, `pid`, `host`, `started` in UTC,
   and a random `token`). It is taken in one atomic step: the folder is made with its owner file under a private name beside
   it, then renamed into place; the rename fails while the lock folder exists (it is never empty, so POSIX cannot replace it;
   Windows refuses any existing target). The folder is under the user's temp folder (`tempfile.gettempdir()`), or under
   `lock_dir` of `agk.toml` when set (Q-337-3a), so one lock serves every project of the machine and is never inside a
   repository. The command runs without a shell (`subprocess.Popen` with its argument list); its exit code is `run`'s, 127 when
   it cannot be started (the message names no value), 130 on Ctrl-C and 143 on SIGTERM (128 + the signal), after the command is
   ended. The lock is released in a `finally`, only when its token is still this run's: it is moved aside under a private name
   and deleted, and put back when the token differs.
2. **Waiting (answer 2).** While another run holds the lock, `run` tries every half second and prints `lock NAME: waiting;
   held by <session> (pid <n>, host <name>) for <m> min` at once and then once a minute, and `lock NAME: taken` when it gets
   it. `--timeout S` gives up after S seconds with `lock NAME: not taken after S s; held by ...` and exit 3 (Q-337-3b); someone
   else's lock is never removed.
3. **Stale locks (answer 3).** A lock is cleared, with `lock NAME: cleared a stale lock of <session> (<reason>)`, when its
   owner's host is this machine and its process id no longer runs (`its process no longer runs`), or when it is older than
   `lock_stale_minutes` (an optional `agk.toml` setting, 120 by default; `older than <n> min, setting: lock_stale_minutes`). A
   lock from another host (a shared `lock_dir`) clears only by age (Q-337-3c). A folder without an owner file clears only by
   its own age. Clearing uses the same move-aside-and-check as the release, so two waiters cannot both remove a fresh lock. A
   bad `lock_stale_minutes` or `lock_dir` is refused with exit 2, naming the setting.
4. **`lock.py status --name NAME` and platforms (answer 4).** It prints `lock NAME: free` or the holder line, with `; stale
   (<reason>)` when a run would clear it, and changes nothing (Q-337-3d). A process is looked up with signal 0 on POSIX and
   with `OpenProcess` and `GetExitCodeProcess` (still active: 259) on Windows, where `os.kill` would end the process; the
   commands are the same in Git Bash and PowerShell. Both settings are read straight from `agk.toml` (`common.config_source`),
   so `common.py` is not changed; `kit/templates/agk.toml` lists them as commented optional lines.
5. **The guide and the session rules (answer 5).** `docs/guides/local-mode.md` replaces its `bash -c` snippet with lines that
   each stand alone: `make governance`, then `lock.py run --name heavy --session <id> -- make test` and the same for
   `proof.py`, with the PowerShell spellings. `tests/kit_dev/test_local_mode_guide.py` (outside `Touches:`) checks the new
   lines instead of the snippet. The session rules: see Q-337-1.
6. **Tests (answer 6).** `tests/kit/test_lock.py`: take and release with the owner recorded; a failing command's exit code and
   release; no shell; a command that cannot start; a second process waits for the first, with one waiting line naming the
   holder; `status`; stale by a dead process id; `status` on a stale lock clears nothing; stale by age; `lock_stale_minutes`
   read and refused; a dead process on another host is not cleared; the timeout; SIGINT and SIGTERM release the lock; the
   default folder; usage; the Windows process check without a signal; the guide and the session rules.
7. **Flow mode.** Fragment `changelog.d/heavy-lock.md`; no version bump; `kit/hashes.json` not edited (session rule 14).

## Consequences

- Two heavy runs on one machine take turns whatever the runtime: the lock is taken and released by one command, so an agent
  that runs lines one by one cannot leave it held, and a lock of a session that died clears itself.
- A lock older than `lock_stale_minutes` is cleared even if its run still goes on; a heavy step longer than two hours needs a
  larger setting.

## Residual

- 2026-10-30: Q-337-1 open: `config/session-rules.md` is also changed by open pull request #346.
- 2026-10-30: Q-337-2 open: `kit/manifest.json` is outside `Touches:`.
- 2026-10-30: Q-337-3 open: the readings (a) to (d) above.
- 2026-10-30: `tests/kit_dev/test_local_mode_guide.py` is outside `Touches:`; its two lock tests follow the guide (decision 5).

# ADR-0191: one kit command takes and releases the heavy-step lock safely (REQ-040, brief 337)

- Status: Accepted
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
   ended, and 128 + n when the command itself is killed by signal n (`kill -9` reads 137, as a shell says; finding 3 of the
   verdict on f9f953f). Taking, clearing and releasing are serialised by a short mutex beside the lock, a folder
   `.agk-lock-NAME.mutex` made with `mkdir` and removed at once; a mutex older than 10 seconds was left by a process that
   died inside it and is removed (finding 1). Under the mutex, a take fails while the lock folder exists, and a clear or a
   release removes the lock only when its token is still the one judged; a lock taken again since then is kept, so two runs
   never hold it. The lock is released in a `finally`, by token. Once the command starts, its process id is added to the
   owner file (`child`), under the mutex (finding 2).
2. **Waiting (answer 2).** While another run holds the lock, `run` tries every half second and prints `lock NAME: waiting;
   held by <session> (pid <n>, host <name>) for <m> min` at once and then once a minute, and `lock NAME: taken` when it gets
   it. `--timeout S` gives up after S seconds with `lock NAME: not taken after S s; held by ...` and exit 3 (Q-337-3b); someone
   else's lock is never removed.
3. **Stale locks (answer 3).** A lock is cleared, with `lock NAME: cleared a stale lock of <session> (<reason>)`, when its
   owner's host is this machine and neither its process id nor its command's (`child`) still runs (`its process no longer
   runs`): a holder killed with SIGKILL leaves its command running, which still holds the machine (finding 2), or when it is older than
   `lock_stale_minutes` (an optional `agk.toml` setting, 120 by default; `older than <n> min, setting: lock_stale_minutes`). A
   lock from another host (a shared `lock_dir`) clears only by age (Q-337-3c). A folder without an owner file clears only by
   its own age. Clearing is the same check under the mutex as the release, so two waiters that judged the same stale lock clear it once. A
   bad `lock_stale_minutes` or `lock_dir` is refused with exit 2, naming the setting.
   `kit/manifest.json` lists `scripts/agk/lock.py` with the verbatim scripts, so a project has it (Q-337-2); it is outside the
   brief's `Touches:`.
4. **`lock.py status --name NAME` and platforms (answer 4).** It prints `lock NAME: free` or the holder line, with `; stale
   (<reason>)` when a run would clear it, and changes nothing (Q-337-3d). A process is looked up with signal 0 on POSIX and
   with `OpenProcess` and `GetExitCodeProcess` (still active: 259) on Windows, where `os.kill` would end the process; the
   commands are the same in Git Bash and PowerShell. Both settings are read straight from `agk.toml` (`common.config_source`),
   so `common.py` is not changed; `kit/templates/agk.toml` lists them as commented optional lines.
5. **The guide and the session rules (answer 5).** `docs/guides/local-mode.md` replaces its `bash -c` snippet with lines that
   each stand alone: `lock.py run --name heavy --session <id> -- make governance AGK_BASE="$base"` (governance runs under the
   lock, as rule 30 says; finding 4), then the same for `make test` and `proof.py`, with the PowerShell spellings. `tests/kit_dev/test_local_mode_guide.py` (outside `Touches:`) checks the new
   lines instead of the snippet (Q-337-4). `docs/guides/reference.md` (outside `Touches:`) names `lock.py` under Local mode,
   which `tests/kit_dev/test_reference_commands.py` (merged from #354) requires of every installed script. Session rule 30 names `lock.py run --name heavy` as the way to take the heavy-step
   lock, and rule 31 says a `prepush.py` run with its tests is a heavy step on a shared machine, run under the same lock
   (Q-337-1).
6. **Tests (answer 6).** `tests/kit/test_lock.py`: take and release with the owner recorded; a failing command's exit code and
   release; no shell; a command that cannot start; a second process waits for the first, with one waiting line naming the
   holder; `status`; stale by a dead process id; `status` on a stale lock clears nothing; stale by age; `lock_stale_minutes`
   read and refused; a dead process on another host is not cleared; the timeout; SIGINT and SIGTERM release the lock; the
   default folder; usage; the Windows process check without a signal; the guide and the session rules. From the verdict on
   f9f953f: two waiters that judge the same stale lock, driven step by step (A clears and takes, B's clear leaves A's lock, C
   cannot take it); the mutex waits and a dead mutex is cleared; a command that outlives a SIGKILLed holder keeps the lock
   until it ends; a command killed by SIGKILL exits 137; the guide's governance line runs under the lock.
7. **Flow mode.** Fragment `changelog.d/heavy-lock.md`; no version bump; `kit/hashes.json` not edited (session rule 14).

## Consequences

- Two heavy runs on one machine take turns whatever the runtime: the lock is taken and released by one command, so an agent
  that runs lines one by one cannot leave it held, and a lock of a session that died clears itself.
- A lock older than `lock_stale_minutes` is cleared even if its run still goes on; a heavy step longer than two hours needs a
  larger setting.

## Residual

- 2026-10-30: Q-337-1 answered in the verdict on 3b9c0a8: rules 30 and 31 change here; if #346 merges first, origin/main is
  merged in and both changes are kept (decision 5).
- 2026-10-30: Q-337-2 answered in the verdict on 3b9c0a8: yes, `kit/manifest.json` lists `scripts/agk/lock.py`, named in the body
  as a change outside `Touches:` (decision 3).
- 2026-10-30: Q-337-3 answered in the verdict on 3b9c0a8: readings (a) to (d) are accepted (decisions 1 to 4).
- 2026-10-30: Q-337-4 answered in the verdict on 3b9c0a8: yes, `tests/kit_dev/test_local_mode_guide.py` checks the new lock lines,
  named in the body as a change outside `Touches:` (decision 5).
- 2026-10-30: the verdict on f9f953f, findings 1 to 4: a short mutex serialises take, clear and release (two waiters could
  let two runs hold the lock); the command's process id is recorded and counts as a holder; a command killed by a signal exits
  128 + n; the guide runs governance under the lock, as rule 30 says (decisions 1, 3, 5, 6).
- 2026-10-30: after #354 merged, `tests/kit_dev/test_reference_commands.py` requires every installed script in the reference;
  `docs/guides/reference.md` names `lock.py` under Local mode (decision 5).

# ADR-0231: the heavy-step lock lets N heavy runs share a machine in priority order, and cleans up after a dead run (REQ-040, brief 426)

- Status: Proposed
- Date: 2026-10-31
- Deciders: maintainers
- Related: ADR-0191, ADR-0227
- Requirements: REQ-040

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`

## Context

Brief #426 (from #288 part 4). `lock.py` (ADR-0191) lets one heavy run hold the machine at a time and clears a stale lock. In
the pilot, memory kills left orphaned containers behind, and a larger machine could carry two runs at once. The steward (#286)
will choose the order of the runs, so the lock must accept one. `prepush.py` (ADR-0227, merged in #422) takes the lock through
lock.py's own `take` and releases it with `clear_if_same`; it must keep working with one slot unchanged. The script, its tests
and the templates are protected path classes, so this ADR names them. The brief names no `Measured:` line. The tests were
written first (`tests/kit/test_lock_slots.py`: 22 failed, 4 passed at the first checkpoint, 1e414c8; the 4 that passed are the
unchanged one-slot paths and the absent cleanup).

## Decision

1. **Slots (answer 1).** `lock_slots` in `agk.toml` is an optional positive whole number, 1 by default (`common.lock_slots`,
   read straight from `agk.toml` as `lock_dir` is, so `DEFAULT_CONFIG` and its tests are unchanged); any other value is refused with exit 2, naming the setting and never the value. Slot 1 is the
   folder `agk-lock-NAME`, as before; slot k is `agk-lock-NAME.k` (a lock name cannot hold a dot, so no other lock's folder is
   ever a slot). `run` takes any free slot, and releases its own slot, found by its token. All slots of a lock, and its
   tickets, share the one mutex of slot 1 (`.agk-lock-NAME.mutex`). Each slot is judged stale and cleared by the rules of
   ADR-0191. With several slots, `status` prints one line per slot, `lock NAME slot k: free` or `lock NAME slot k: held by
   ...`, and the waiting line names each held slot (`slot k held by ...`). With one slot nothing changes: the folder, the
   `status` line and the waiting line are as before.
2. **Priority order (answer 2).** `run --priority P` takes 0 to 3, 2 by default, as for briefs; any other value is a usage
   error (exit 2). Under the mutex, a run looks at the other runs' tickets in `.agk-lock-NAME.tickets/`; it takes a free slot
   only when fewer runs go before it than there are free slots, and otherwise writes its own ticket (`session`, `pid`,
   `host`, `priority`, `created` in nanoseconds, `token`; written whole, then moved into place) and waits. A free slot goes
   to the lowest priority, then to the oldest ticket (then the token, so the order is total). A ticket whose process no
   longer runs on this machine is dropped with `lock NAME: dropped the ticket of <session> (its process no longer runs)`; a
   ticket that cannot be read is a leftover and is dropped too. A run removes its own ticket when it takes a slot, gives up
   (`--timeout`) or is interrupted, and the ticket folder goes when it is empty. While runs go before it, the waiting line
   says `<n> waiting run(s) go(es) first`. `take` keeps its arguments; called as `prepush.py` calls it, it is the one-slot
   lock with a ticket at the default priority and no cleanup, and it returns the slot's folder (a true value) or None.
3. **Cleanup (answer 3).** `lock_cleanup` in `agk.toml` is an optional command line, empty by default; the kit ships none, and
   a value that is not a string is refused naming the setting. When `run` clears the lock of a run whose process no longer
   runs on this machine, the cleanup runs once (by the run that cleared it), through `sh -c` in the repository's top folder,
   with `AGK_LOCK_SESSION` and `AGK_LOCK_PID` of the dead holder. Its output is shown as it comes. It ends with `lock NAME:
   cleanup of <session> done (setting: lock_cleanup)`, or a failure is reported (`failed (exit n, ...)`, `cannot be started`,
   or `did not end within 300 s and was stopped`, its process group ended) and the run goes on to take its slot. It is not
   run, with a line saying why, for a lock that names no session, or for one cleared by age, whose run may still go on
   (Q-426-2). The locked command gets `AGK_LOCK_SESSION` (the run's session, or empty), so a project can label what it starts
   by session. The templates (`kit/templates/agk.toml`, `kit/templates/agk.adopt.toml`) list `# lock_slots = 1` and
   `# lock_cleanup = ""` with an invented example, `docker ps -aq --filter label=agk.session=$AGK_LOCK_SESSION | xargs -r
   docker rm -f`; the adopt template gains the existing `lock_dir` and `lock_stale_minutes` lines with them, so both say the
   same. `docs/guides/reference.md` describes the settings and `--priority`.
4. **Tests (answer 4).** `tests/kit/test_lock_slots.py`: two slots held by two processes while a third waits (and `status`
   per slot); priority order between two waiting runs, and the oldest ticket at the same priority; a dead ticket dropped; a
   live ticket of a higher priority goes first; cleanup run on a stale clear with both variables, its output shown; a failing
   cleanup reported and not blocking; no cleanup by age or without a session; no cleanup when unset; the command's
   `AGK_LOCK_SESSION`; one slot unchanged (folder, `status`, `lock_folder`); `take` as `prepush.py` calls it; refusals of
   `lock_slots`, `lock_cleanup` and `--priority`; the templates and the reference. `tests/kit/test_lock.py` and
   `tests/kit/test_prepush_regression.py` pass unchanged.
5. **Flow mode.** One changelog fragment of one line, `changelog.d/lock-slots.md`; no version bump; `kit/hashes.json` not
   edited (session rule 14).

## Consequences

- A machine that can carry two heavy runs sets `lock_slots = 2`, and a run the steward marks urgent goes first.
- A project that labels its containers by `AGK_LOCK_SESSION` and sets `lock_cleanup` gets them removed when a run died.
- With one slot and no cleanup, the lock behaves as before, except that waiting runs now take their turn in ticket order
  instead of by chance.
- `prepush.py` still takes only slot 1 (Q-426-1).

## Residual

- Q-426-1 (2026-10-31): `prepush.py` (outside `Touches`) calls `take` and `clear_if_same` on slot 1 only, and recognises its
  caller's lock only in slot 1. With `lock_slots` above 1 its own take waits for slot 1 alone (its ticket still counts in the
  order), and under `lock.py run --name heavy` it does not see a caller that holds slot 2. With one slot it works unchanged.
  A follow-up brief may let it take any slot; not changed here.
- Q-426-2 (2026-10-31): answer 3 says the cleanup runs "when a stale lock is cleared", and the brief's sentence speaks of "a
  dead run's lock". Read conservatively, it runs only for a lock cleared because its process no longer runs: a lock cleared
  by age may belong to a run that still goes on (another machine, or a run longer than `lock_stale_minutes`), and a lock that
  names no session gives the cleanup nothing to aim at (an empty `AGK_LOCK_SESSION` could match everything).
- Q-426-3 (2026-10-31): the brief says a failing cleanup never blocks but names no time limit; a cleanup that hangs would
  block the waiting run. It is stopped after 300 s and reported as a failure. A setting for the limit is not added.
- Q-426-4 (2026-10-31): a ticket from another host (a shared `lock_dir`) is never dropped, since its process cannot be looked
  up from here; the brief names only "a process that no longer runs".

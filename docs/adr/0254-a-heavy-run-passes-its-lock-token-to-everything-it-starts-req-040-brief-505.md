# ADR-0254: A heavy run passes its lock token to everything it starts (REQ-040, brief 505)

- Status: Accepted
- Date: 2026-11-03
- Deciders: maintainers
- Related: ADR-0191, ADR-0231, ADR-0186
- Requirements: REQ-040

Protected classes: `scripts/agk/`, `config/`, `tests/kit/`

## Context

`prepush.py` treats the heavy-step lock as its caller's only when `lock.py` is its direct parent (the owner's `child`
is this process, or the owner's `pid` is this process's parent). In the pilot (#478) a session wrapped
`prepush.py --record` in its own script under `lock.py run --name heavy`, so a wrapper process sat between them;
prepush did not recognise the slot and waited on its own lock for about 50 minutes with no message. Brief #505 asks
for the lock to travel down by its token. This ADR number was reserved for brief #505 by the conductor (the field note
on #505).

## Decision

1. `lock.py run` gives the command it starts `AGK_LOCK_TOKEN`, the token of the slot taken, and `AGK_LOCK_NAME`,
   beside `AGK_LOCK_SESSION`; every process below it inherits them. The token is a random value with no secret
   meaning, and no script prints it.
2. `prepush.py` treats a slot as its caller's also when, on the same host, the owner's `token` equals
   `AGK_LOCK_TOKEN` and the lock's name equals `AGK_LOCK_NAME`, and prints the existing line
   `lock heavy: held by this run's caller (lock.py run); not taken again`. The direct-parent rule stays.
3. When no slot is the caller's and a slot is held, in another process and not stale, by an owner whose
   `session` is the same non-empty `AGK_SESSION` as this run's, prepush does not wait: the tests step fails at once
   with the one line `lock heavy: held by this session (<session>) in another process; run prepush directly under
   lock.py run --name heavy, or end that run first`. A slot held by another session is waited for as before.
4. Session rule 31 says that a wrapper between `lock.py run` and prepush is allowed, because the token passes down.

## Consequences

A session never waits on its own heavy lock: through any number of wrappers the token finds the slot, and where the
token cannot reach (a run started outside `lock.py run`, or an environment that drops the variable) the same session's
run fails in seconds with a line that names the fix instead of waiting in silence. Slots, cleanup and stale handling
are unchanged; a stale slot of the same session is still cleared by `take` as before.

## Residual

- 2026-11-03: the same-session failure reads `AGK_SESSION` only, as the brief names it; a run that sets only
  `lock.py run --session ID` without `AGK_SESSION` in its environment is not caught by answer 3 (Q-505-1).

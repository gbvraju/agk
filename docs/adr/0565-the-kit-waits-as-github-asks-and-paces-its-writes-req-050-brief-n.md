# ADR-0565: The kit waits as GitHub asks, and paces and counts its own writes

- Status: Accepted
- Date: 2026-11-15
- Deciders: maintainers
- Related: brief #1335, brief #210, brief #1251, ADR-0529, ADR-0548, plan #661
- Requirements: REQ-050

## Context

Brief #1335 found that `scripts/agk/session.py` `gh()`, on a call that GitHub limited, read `GET rate_limit` and
slept until the core limit's reset, up to `RATE_WAITS` times. A secondary limit can strike while the core limit
has thousands of calls left, so a wait that GitHub set at about a minute could last up to an hour. Two writes of
one process followed each other with no pause, and no run counted its writes. GitHub's REST guidance asks a
client to wait the `retry-after` seconds when given, until `x-ratelimit-reset` when `x-ratelimit-remaining` is 0,
and otherwise at least one minute with an exponential back-off, and to leave at least one second between two
mutating requests `(verify: the header names and the one-minute floor)`.

## Decision

1. On a limited call (`rate limit` or `HTTP 429` in what `gh` says, or a 429 status), `gh()` waits, in this order:
   the `retry-after` seconds when positive; else until the `x-ratelimit-reset` time plus `RESET_SLACK` when
   `x-ratelimit-remaining` is 0 (the primary limit); else `SECONDARY_WAIT` (60) seconds, doubled on each further
   secondary try of the same call, up to `RATE_WAITS`. The headers come from the same call: the reads that already
   ask with `gh api -i` (the cached GETs, ADR-0548). When no header can be read (a write, a read with extra
   arguments, or no status line), `GET rate_limit` answers the same order: a core `remaining` of 0, or none given,
   is the primary limit as before; any other is a secondary limit and waits 60 seconds, doubled. When
   `rate_limit` cannot be read either, the call fails as before.
2. A secondary wait above `SECONDARY_CAP` (15 minutes) is cut to 15 minutes, after which the call counts as
   failed and the caller's existing unreadable path runs; a primary wait is taken as given. A `retry-after` of 0
   or one that is not a number falls to the next rule. A 304 never waits, and a read that the run's memo or the
   read cache answers makes no request and never waits.
3. Each wait prints one line on standard error, `github: limited, waiting <n> s (<primary|secondary>)`, naming no
   token and no URL.
4. Two mutating calls (`POST`, `PATCH`, `PUT`, `DELETE`) of one process are at least `WRITE_GAP` (one second)
   apart; reads are never delayed. The gap is a constant, not a setting.
5. `session.WRITES` counts a run's mutating calls. `session.py plan` puts the plan's writes in its `reads`
   figures when above 0, its `reads:` line then ends `, writes: <n>`, and `checklist.py` point 8 shows
   `, writes <n>` beside the plan's reads. Nothing is refused on the count.

## Consequences

A secondary limit no longer sleeps to the core reset, and the kit's own bursts of posts are spread out by one
second each. A write carries no `-i`, so its limit is told from `GET rate_limit` and not from its own
`retry-after`; adding `-i` to writes would change the recorded arguments of every write in the kit's tests.
Protected path classes changed: `scripts/agk/` (`session.py`, `session_plan.py`, `checklist.py`), `tests/kit/`
(`test_github_rate_wait.py`) and `agk.toml` (the new test file in the `[[testing.map]]` entries of the three
scripts).

## Residual

- 2026-11-15: Q-1335-1: brief #1335 answer 1 reads every limited call's headers from the call itself; here a
  write's `retry-after` is not read (decision 1), the write asks `GET rate_limit` instead, and a write limited by a
  secondary limit waits 60 seconds, doubled, rather than the seconds GitHub asked. Reading them would add `-i` to
  every write and change the recorded arguments of the writes in about 44 test files; the question is open.

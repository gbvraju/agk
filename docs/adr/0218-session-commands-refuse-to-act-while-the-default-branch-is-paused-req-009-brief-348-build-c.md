# ADR-0218: session commands refuse to act while the default branch is paused (REQ-009, brief 348 build c)

- Status: Accepted
- Date: 2026-10-30
- Deciders: maintainers
- Related: ADR-0196, ADR-0203
- Requirements: REQ-009

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #348 build (a) (ADR-0196) made `paused = true` in `agk.toml` stop the checks, the router and, through session rule 33, the
sessions themselves. Rule 33 relies on each session running `doctor.py --paused` first; a session that skips it, or a launcher
that calls `session.py` directly, could still take a brief, list work or wait on a pull request. Q-348-2 asked for `session.py` to
refuse `claim`, `next`, `queue` and `watch` while paused; the conductor's field notes on #348 make that build (c), the last build,
reading the default branch as rule 33 does and naming the setting in its refusal.

## Decision

1. **The refused commands (Q-348-2).** While the setting is on, `session.py claim`, `next`, `queue`, `watch` (all of `--pr`,
   `--merged` and `--assign`) and `after` print one line that starts `agk paused` and names the setting (`setting: paused in
   agk.toml of the default branch`), call no `gh`, post nothing and exit 5, a code no other outcome of these commands uses.
   `after` is refused too because it runs `next` or starts the wait on an `Assign:` line (session rule 18). The other commands
   (`ids`, `demand`, `plan`, `push-check`, `resume`, `review-queue`, `tell`, `inbox`) are unchanged: none of them takes or waits.
2. **Read on the default branch (Q-348-2).** The setting is read with `common.paused` at the ref `origin/<default_branch>`
   (`default_branch` in `agk.toml`), which the `git fetch` of session rule 33 keeps current. `session.py` does not fetch itself:
   rule 33 has just fetched, and a fetch from the commands would add a network call to every test that runs them. A branch made
   before the pause merged is therefore refused, and the branch that adds `paused = true` is not, so its own pull request can
   still be claimed, watched and reviewed.
3. **No fetched default branch (Q-348-4).** When the ref `origin/<default_branch>` does not exist (a checkout that was never
   fetched), the checkout's own `agk.toml` is read instead, the only copy at hand.
4. **A bad value.** A value that is not `true` or `false` is refused as `common.paused` refuses it, by the setting's name and
   never the value, exit 2, before any call to GitHub.
5. **Tests first.** `tests/kit/test_session_paused.py` covers each refused command with no `gh` call, a branch older than the
   pause, the branch that adds it, resuming, the missing ref, a bad value and a command that is not refused.

## Consequences

No session takes, lists or waits on work while the kit is paused, even one that does not run the doctor first; a `watch` started
before the pause ends at its next event and the session's rule 33 check then stops it. Removing the line resumes the commands at
once. The rule text is unchanged: rule 33 already says what a session does while paused.

## Residual

- 2026-10-30: Q-348-4 (decision 3): the checkout is read when the default branch was never fetched; the conservative
  alternative, refusing, would stop every session in a checkout without the ref.
- 2026-10-30: a `watch` already waiting when the pause merges is not ended by it (decision 1 checks at the start only).

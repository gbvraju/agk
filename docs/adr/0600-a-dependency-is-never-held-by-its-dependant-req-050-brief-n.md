# ADR-0600: A dependency is never held back by its dependant

- Status: Accepted
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1432, brief #1431, brief #1424, PR #1429, SPEC-0050 rules 2 and 4, ADR-0325
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0050 rule 2 holds a brief back from every taken brief and open builder pull request whose files overlap it, and
rule 4 makes `plan`, `next` and `claim` share that one judgement (`session_plan.running_conflict`). It never read the
holder's `Depends-on:` lines. On 2026-11-17 the taken red-main repair #1424 (`Touches: **`) had a release pull
request #1429 carrying `Depends-on: #1431`, and `claim` refused #1431 with `waits for #1424`: neither could move and
main stayed red until the owner answered by hand.

## Decision

1. **Dependency beats overlap.** A holder does not hold brief #n back when the holder waits on #n: its taken brief's
   body or its open pull request's body has `Depends-on: #n`, or either depends on #n down a chain of `Depends-on:`
   lines among open briefs. The chain is built once per survey from the bodies already read (no GitHub call). The
   brief starts with the line `#n starts ahead of #h, which depends on it (overlap on <file> ignored)`, printed by
   `plan` (and in `plan --json` under `ahead`, a key present only when a dependency is lifted, so the plan is otherwise as before), `next` and `claim`.
2. **Only the dependency is lifted.** Every other overlapping holder still holds the brief; the holder is neither
   restarted nor stopped. The plan's `Holds` lines leave out a lifted hold, so they agree with the judgement.
3. **A real cycle is reported.** When #n also waits on the holder, the wait is
   `CYCLE: #a and #b wait on each other (Depends-on); the owner chooses which goes first` and nothing starts. A brief
   that `next` and `plan` skip as `depends on #d, which is open` where #d's chain comes back to it is said the same way.
   `plan` prints each cycle once and `plan --json` lists it under `cycles` with the line
   `Owner needed: #a and #b wait on each other (Depends-on); remove one of: <the Depends-on lines of the loop>`.
4. **Only open, valid lines count.** A `Depends-on:` naming a closed item, a pull request, an item that is not an open
   brief, the brief itself or a malformed number is ignored for this rule, as `depends_on` ignores it.

This narrows SPEC-0050 rule 2's overlap by one exception and keeps rule 4: the three commands still share one
judgement. The new test file is added to the `[testing]` map of `agk.toml` for `scripts/agk/session.py` and
`scripts/agk/session_plan.py`, as the test-map check requires.

## Consequences

A red-main repair whose fix waits on it no longer deadlocks. The bodies come from the plan's existing reads, so the
number of GitHub calls is unchanged. Personal mode reads the sidecar's briefs and pull request bodies through the
files forge into the same survey, so the rule applies there unchanged.

## Residual

- 2026-11-17: the conductor posting the `Owner needed:` line from `plan --json`'s `cycles` is not wired in this build
  (`conductor.py` is outside the brief's `Touches:`); asked as Q-1432-1.

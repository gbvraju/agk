# ADR-0607: Only a verdict author's machine starts a conductor; other machines run builders only

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1449, ADR-0330, ADR-0592, ADR-0525, ADR-0554, ADR-0559, SPEC-0064, SPEC-0065
- Requirements: REQ-071

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The lease on the plan issue counts only a marker by a listed verdict author (ADR-0330 decision 3), and a verdict counts
only from one (`config/reviewers.yaml`). The kit's conductor starts (`conductor.py watchdog` of ADR-0525, `watchdog
--pass` of ADR-0554 and `launch.py role --role conductor` of ADR-0559, which the autopilot uses) start a conductor
whenever the counted lease is free and never compare the machine's own login with `verdict_authors`. In a team whose
members each run the autopilot, a member's machine therefore starts a conductor whose lease marker the others ignore
and whose verdicts do not count, at every pass while the lead's lease is free. ADR-0592 holds one conductor per
machine; it says nothing about which machines may run one.

## Decision

1. **Who may start a conductor.** Before a conductor start the kit makes, it reads the signed-in login with one
   `gh api user` (`launch.signed_in_login`, cached for the run and the checkout, compared in lower case and never
   printed) and starts a conductor only when that login is in `verdict_authors` as `reviewers.authors_of` reads it: the
   list, else the user handle of the `maintainers` team. Otherwise it prints
   `watchdog: this login is not a verdict author; conductor not started, builders only (setting: verdict_authors in
   config/reviewers.yaml)` and the pass goes on to its builder checks (ADR-0568). `launch.py role --role conductor`
   prints `stuck: conductor <session> not started (<the same text>)` and exits 1.
2. **Where it is read.** The plain watchdog reads it after it finds the lease free; the scripted pass reads it after
   its change reads find work and before it takes the lease, so a member's machine posts no lease marker and a quiet pass
   costs no extra read. On a member's machine the scripted pass starts no steward job either: the steward stands beside
   the owner (SPEC-0059), and the pass that starts it is the conductor's.
3. **Unknown login.** When the login cannot be read, no conductor starts and the line says `this login is unknown`;
   builders run as before.
4. **Unchanged.** Solo mode (its one listed person is the verdict author), the lease between machines (ADR-0330), one
   conductor per machine (ADR-0592), a conductor a person starts by hand (never stopped, never gated), the steward's own
   `launch.py role --role steward` start, and personal mode, which runs no conductor. Hosted mode's conductor start goes
   through `launch.py role` and gets the same check; no workflow changes.

## Consequences

A team can run the autopilot on every machine: only the lead's machines start a conductor, and the others print one
line and run builders, so no conductor runs whose lease and verdicts do not count. A conductor start costs one more
read of GitHub per run.

## Residual

- SPEC-0065 rule 14 build (h) settles the roles per machine and reuses this check.

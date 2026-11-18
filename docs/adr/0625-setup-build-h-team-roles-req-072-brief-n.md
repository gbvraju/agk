# ADR-0625: /agk:setup build (h): each team machine gets exactly the roles the repository allows

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: SPEC-0065, ADR-0607, ADR-0618, ADR-0619, brief #1467, plan #661
- Requirements: REQ-072

## Context

SPEC-0065 (Approved) names eight builds of `/agk:setup` (rule 18); this is build (h), the last: rule 14's roles of
each machine, decided from the repository, and rule 15's restart of a machine's stopped roles and the team-wide
read-only status. Before it, `setup.py --json` printed `roles` empty, and nothing told a team member's machine whether
it may run a conductor or a steward.

## Decision

1. **The roles of a machine.** `setup.py` reads the signed-in login with brief #1449's reader (`common.signed_in_login`,
   one `gh api user` per run), compares it with `verdict_authors` through `common.is_verdict_author`, the one comparison
   that `common.conductor_refusal` now also calls, and with `spec_approvers` of `config/reviewers.yaml`, keeps only the
   result (`author`, `reviewer`, `other`, `unknown`) and never prints or stores the login. The roles follow rule 14:
   every role in solo mode; the steward only for a listed reviewer and only while no steward is live; the conductor only
   for a verdict author and only when the lease reads `free` (a held, `off` or unreadable lease starts no conductor, so
   there is never a second one); builders on every machine, sized by rule 6 and capped by `max_builders` less the team's
   live builders. `review_mode` decides solo or team; the person's `team` answer counts only while it is unset, so an
   answer never widens the roles. A non-reviewer's machine with no live conductor gets builders only and the line `the
   conductor waits for a verdict author's machine`. For me only and on GitHub's machines no role runs here (rule 16).
   `--json` prints `roles` and `roles_why`; the plan's last line names them. `--roles A,B` lowers the set; a role
   outside it is refused naming the settings.
2. **The restart.** A new form `setup.py restart` restarts exactly those roles: without `--yes` it names them and starts
   nothing (exit 1); with `--yes` the conductor by one `conductor.py watchdog --conductor-only` start, which checks the
   lease and the verdict author again (ADR-0607) and, with the new flag, runs no builder pass, so no builder restarts
   without `/agk:launch`'s yes. The conductor's row is `done` only when the watchdog prints its `watchdog: started`
   line; any other run (the lease taken meanwhile, the login refused, a conductor already running here) is `waiting`
   with the watchdog's own last line, and a non-zero exit `failed`. The builders by a `waiting` row that sends the
   person to `/agk:launch`'s own plan and yes, and the steward by a `waiting` row that prints `claude --agent steward`,
   since the steward is the person's own session (`Q-S0065-11`). A builders-only machine runs no watchdog.
3. **The team status.** `setup.py status` adds the team as the repository records it: the lease holder, the live
   steward, each running builder with its brief (from `session.py plan --json`), the number of members listed, the
   pull requests that wait for a verdict and this machine's roles (`--json`: `team`). It is read-only and posts
   nothing; no login is printed.
4. **The skill.** `skills/setup/SKILL.md` gains the restart form, the team lines of the status form and `--roles`.

## Consequences

Any team member can run `/agk:setup` and get only the roles the repository allows, restart them after a stop and see
the whole team, with no second conductor and no steward for a non-reviewer. Protected path classes changed:
`scripts/agk/` (`setup.py`; `conductor.py`, the `--conductor-only` flag of `watchdog`; `common.py`,
`is_verdict_author`), `tests/kit/` (`test_setup_team_roles.py`), `skills/` (`skills/setup/SKILL.md`) and
`agk.toml` (the `[[testing.map]]` entries for `setup.py`, `conductor.py` and `common.py` gain the new test file).

## Residual

- 2026-11-18: the steward cache records no author for a `Started: steward` comment, so any live steward withholds the
  steward role from this machine, as `steward.py start` refuses a second one today; the per-login reading of SPEC-0063
  rule 4 follows when that build lands (Q-1467-1).
- 2026-11-18 (verify): the roles and the restart have run only against saved GitHub answers and a stub runner; a
  person's run on a team of machines confirms them (due 2027-03-31).

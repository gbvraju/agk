# ADR-0653: Which GitHub jobs a repository runs is one setting, full, events or off (REQ-039)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: SPEC-0032, amendment 190, brief #1555, brief #1554, ADR-0654, brief #1539, brief #1534, SPEC-0039, SPEC-0064, SPEC-0071, SPEC-0072, plan #661
- Requirements: REQ-039

Protected classes the builds of this decision change: `.github/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`,
`kit/`, and `agk.toml` when the kit sets its own value. This pull request changes none of them.

## Context

On the default branch at a948d695 (2026-11-20) the only switch for the kit's GitHub workflows is all or nothing:
`local_mode.py enter --write` disables every active workflow and `leave` enables them again. A private repository with
every workflow enabled billed about 1,237 minutes a day in the kit (brief #1554's window), about 1,171 after ADR-0654.
Most of that is governance and proof, which a local-mode repository (`execution = "local"`) does not need, since
`merge_cleared.py` reads local evidence there (SPEC-0039 rule 4). The two small comment jobs (the router and the merger)
are what keeps the labels and the unparks fast.

A job `if:` can read a repository variable and no file, and a job skipped by its `if:` bills nothing; only a disabled
workflow creates no run. The ruleset requires `governance`, so with governance not running every merge is held until
the owner changes the ruleset or merges by hand. And with governance and the router off, nothing raises "The default
branch is red" or closes the brief after a merge that a person makes.

The owner asked for a setting rather than a hard switch, with `events` as the private default and `off` on clean-layout
projects (brief #1555, quoted there as data).

## Decision

1. SPEC-0032 changes only through amendment 190, which this intake writes and does not apply. It adds rule 15 (the
   setting `actions = "full" | "events" | "off"`, absent `full`, read by each kit workflow's job `if:` through the
   repository variable `AGK_ACTIONS`), one sentence each to rules 1, 7 and 8, one test line, and rewrites the `github`
   and `local` entries of the `## Contexts` section.
2. `events` and `off` are refused unless `execution = "local"`; a clean-layout project takes `off` only; personal mode
   refuses the setting. Each refusal names the setting, never a value (principle 8).
3. No value posts a status or a check run for a check that did not run (principles 2 and 11), and no session changes the
   ruleset. Under `events` and `off` the ruleset holds each merge until the owner changes it, and `doctor.py` says so.
4. One command, `local_mode.py actions full|events|off [--write]`, sets the variable and enables or disables the kit's
   workflows only, refuses `--write` inside an agent session and while the value differs from `actions` on the default
   branch.
5. Each thing `events` or `off` turns off has a named owner (amendment 190's table): the conductor's `route.py --all`
   for labels, the supervisor's pass for unparks, and a new after-merge pass of the supervisor for the red-branch issue,
   the brief close and the health issues after a merge no guarded merge checked.
6. The default that setup and `/agk:upgrade` propose, for a person to confirm: `full` for a public repository, `events`
   for a private one, `off` for a clean-layout project. Nothing switches on its own.
7. `AGK_MERGER` (ADR-0654) stays independent of `AGK_ACTIONS`.
8. The builds (a) to (e) of amendment 190 follow by the `brief` skill, each from the default branch, tests first; build
   (b) changes the workflows and the owner merges it by hand (session rule 30).

## Consequences

- A project that sets neither the key nor the variable sees no change.
- In the kit, `events` bills about 279 minutes a day and `off` none, against about 1,171 for `full` after ADR-0654.
- Under `events` and `off` a merge waits for the owner's change of the ruleset or the admin's merge, and a push waits for
  the conductor's pass to relabel.
- A mismatch between the setting and the variable follows the variable and is reported by `doctor.py`.

## Residual

- 2026-11-20: until build (d) lands, a person's merge under `events` or `off` raises no red-branch issue and closes no
  brief; doctor warns and the runbook names `failures.py run --on default` (due 2026-12-31).
- 2026-11-20: the permission to read a repository variable and the precedence of an organisation variable of the same
  name are marked (verify) and checked at build (a) (due 2026-12-31).

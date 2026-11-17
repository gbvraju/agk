# ADR-0623: /agk:setup build (f): CI mode checks the repository with GET calls only and installs nothing

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: SPEC-0065, ADR-0618, ADR-0619, ADR-0620, brief #1465, plan #661
- Requirements: REQ-072

## Context

SPEC-0065 (Approved) names eight builds of `/agk:setup` (rule 18); this is build (f): CI mode's repository checks (rule
10, with rule 16's CI case). For `execution = "hosted"` the AI work runs on GitHub's machines, so the command installs
nothing on this machine and checks the repository instead, with GET calls only, naming each missing item for the owner
by its setting and never creating, reading, printing or storing a secret or token.

## Decision

1. **`setup.py ci`**, a new form of the kit-only helper, runs only when `agk.toml` holds `execution = "hosted"` (the
   default when the key is absent); any other value, or no `agk.toml`, is refused naming the setting `execution`, and
   nothing is called. A folder with no GitHub remote stops with one line and no call.
2. **Four checks, each a `gh api -X GET` call and nothing else:** `actions` (`actions/permissions`: enabled),
   `workflows` (`actions/workflows`: each workflow of `kit/manifest.json`'s `verbatim` list under `.github/workflows/`
   present and `active`), `rules` (`rulesets` non-empty, or the default branch read from the repository shown as
   `protected`) and `secrets` (only with `[flow] auto_merge = true`: a secret listed in the `merge` environment, the
   merger's; only the list is read, by count, and no name or value is kept or printed). Each row is `skipped` when met
   and `waiting` when not, as the table of rule 2 is; `--json` prints `steps`, `pending`, `roles` (empty), `builders`
   (none: nothing is sized from this machine in CI mode) and `missing`.
3. **One line per missing item for the owner**, `missing: <what> (setting: <setting>)`, the setting being `Actions
   permissions`, `the kit's workflows`, `kit/templates/ruleset.json` or `auto_merge`. An answer GitHub does not give to
   this sign-in (a refused or failed call) is `unknown` with a note, never counted as missing (a figure that cannot be
   read is unknown, never 0). Exit 0 when every check is met, else 1.
4. **Installs nothing.** The form calls no package manager and runs no command but the GET calls; `install` is left as
   build (c) made it (Q-1465-1).

## Consequences

A project run on GitHub's machines learns, in one table, what its repository still lacks for the kit, without any change
to the machine, the repository, a workflow, the ruleset, a required check or a secret. Protected path classes changed:
`scripts/agk/` (`setup.py`), `tests/kit/` (`test_setup_ci.py`) and `agk.toml` (the `[[testing.map]]` entry for
`setup.py`).

## Residual

- 2026-11-17 (verify): the four GET routes and the fields read (`enabled`, `state`, `protected`, `secrets`) have run
  only against saved answers; reading `actions/permissions` and an environment's secrets may need an administrator's
  sign-in, which shows as `unknown` (due 2027-03-31).
- 2026-11-17: the skill `skills/setup/SKILL.md` does not yet call the `ci` form; the brief's `Touches:` leaves it out.

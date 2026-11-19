# ADR-0639: Personal mode build (o): `[governance] level` in team mode, with the floor fixed at every level

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: brief #1509, SPEC-0041 rules 17, 18, 30 (o) and 31, ADR-0267, ADR-0280, ADR-0306, Q-562-1, Q-562-2
- Requirements: REQ-048

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `agk.toml`

## Context

SPEC-0041 rule 31 (amendment 119, the owner's ruling D2 on plan #542) brings the five levels of rule 17 to team mode
through a `[governance] level` setting, `light` for a new install, with the floor of rule 18 fixed in both modes and at
every level. Before this build no `[governance]` table was read anywhere: not in `common.py`, `doctor.py` or the two
templates the installer writes. Rule 31 leaves to this build which team-mode checks a level leaves out (`Q-562-1`) and
whether a team-mode `prepush.py` without gitleaks fails the floor (`Q-562-2`). This is build (o) of rule 30's order
(ADR-0267).

## Decision

1. `common.governance_level(root)` reads the table. It accepts exactly one key, `level`, with one of the five values of
   rule 17 (`common.GOVERNANCE_LEVELS`, the same tuple as `[personal] level`). A `governance` value that is not a table,
   any other key (for example `skip_floor`), a value of the wrong type and an unknown value are refused, one line naming
   `governance`, `governance.<key>` or `governance.level`, never the value (principles 8 and 11). With no table, no key,
   or settings that hold `[personal]` (a sidecar, rule 17), it returns None and nothing changes.
2. `doctor.py` prints one information line after the secret scan line, `governance level: <level> (the floor, the
   secret scan and no regression, runs at every level)`, and the same text as `governance_level` in `--json`, when a
   level is set. With none set it prints nothing new, so the pinned output of an existing project is unchanged. A
   refused table stops the doctor, exit 1, before any other check.
3. `kit/templates/agk.toml` and `kit/templates/agk.adopt.toml` write `governance = { level = "light" }` (an inline
   table: the same `[governance]` table in TOML) right after `review_mode`, so `init.py` and `adopt.py` set up a new
   project at `light`. The line sits among the top-level keys and not as a `[governance]` header at the end of the
   file, because a header at the end would take into the table any top-level line a person or a tool later appends.
4. What a level leaves out (`Q-562-1`). This build leaves out no check at any level: `common.GOVERNANCE_SKIPS` maps
   each level to an empty tuple, and no check reads the level yet. The candidates for a person to rule on, check by
   check, are recorded as `Q-1509-1`; until that ruling, the conservative reading of rule 31 holds and every existing
   team-mode check runs as before.
5. The floor (`Q-562-2`). The floor is the secret scan and no regression, at every level. ADR-0306 (Accepted) already
   makes the secret scan mandatory in every mode: a `prepush.py` without gitleaks fails the run, naming the tool. This
   build changes nothing there, so `Q-562-2` is answered by ADR-0306 and today's behaviour stands.
6. `agk.toml` maps `tests/kit/test_governance_level.py` to `scripts/agk/common.py` and `scripts/agk/doctor.py`.

## Consequences

- A new install shows `governance level: light` in the doctor; an existing install shows nothing until it sets the
  key, and runs every check as before.
- No setting can lower the floor: the only accepted key is `level`, and no level leaves out a check.
- No workflow, ruleset or required check changes, and personal mode is unchanged.

## Residual

- `Q-1509-1`: which team-mode checks `tests-first`, `spec`, `review` and `evidence` add, and which `light` leaves out,
  each needs a ruling and its own build.

# ADR-0470: A brief runs on its kind's tier, and the route of that tier can be read

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0045, SPEC-0006, ADR-0289, ADR-0402, amendment 145, amendment 165, brief #1099, plan #661
- Requirements: REQ-052

## Context

The owner named model per kind of work as the biggest gap of the nine-point checklist: every task runs on the most
expensive model (brief #1099). SPEC-0045 rule 4 gives `design` to any brief whose `Touches:` or `Adds:` may match
`docs/adr/`, and nearly every brief names its own reserved ADR there, so `session.py kind` printed `design` for every open
brief on 2026-11-12. Amendment 145 put a `[models.routes]` table (rule 3), the route of a tier (rule 5) and a
`model-routes` doctor row (SPEC-0006 rule 5) into the Approved text, but no code reads them.

## Decision

1. Rule 4 as amendment 165 proposes: a glob whose literal start is `docs/adr/<n>-`, for an `ADR-<n>` of the brief's one
   `Reserved:` line with no ADR of that number in `docs/adr/`, is the brief's own new ADR and does not by itself give
   `design`; every other path of rule 4's list still does (`session.kind_of`, `session.own_adrs`).
2. Build (f) of SPEC-0045 in part (brief #1099 answer 2): `config.model_routes` reads and refuses rule 3's table, naming
   `setting: models.routes` or `setting: models.routes.<tier>`; `config.route_of` gives a tier's route or the next
   stronger one (rule 5); `python3 scripts/agk/session.py route --brief N` prints `route: <tier> <effort> task <label>`
   (or `flag`, or `slots ...`), with ` via <tier>` when moved, or `route: none` with no table; `doctor.py` gains the
   `model-routes` row, severity `warn`. The prompt's route, `AGK_ROUTE`, the plan's slot pairing and the conductor's
   re-fire line are left for a later build (answer 2).
3. This repository's `agk.toml` carries no `[models.routes]` until the maintainers answer `Q-1099-1`: rule 3 refuses
   the kit's own table, a `task` route under `builder_start = "assign"`, and labels with spaces. The templates carry a
   commented example with plain labels and no model name.

Protected path classes changed: `scripts/agk/` (`config.py`, `session.py`, `doctor.py`), `tests/kit/`
(`test_model_routes.py`, `test_models_table.py`, and the doctor counts in `test_doctor.py` and
`test_delivery_declaration.py`), `agk.toml` (the test map only) and `kit/` (the two templates' comment).

## Consequences

A `Size: S` brief whose only ADR is its own prints `small` and runs on `mid` at `low`; nothing is lowered (rule 1):
reviews stay on `strongest` and a `mid` builder escalates by rule 5. `route` gives a launcher the scheduled task of a
brief's tier; with no table it prints `route: none` and nothing changes. Creating the scheduled tasks and the
launcher's use of `route` are the co-owner's, after this merges.

## Residual

- 2026-11-12: a brief may use its own ADR to decide more than its brief says; the conductor may raise its kind (rule 4)
  and the review reads the ADR as before (due 2027-01-31).

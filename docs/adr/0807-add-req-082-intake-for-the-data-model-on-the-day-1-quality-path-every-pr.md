# ADR-0807: Add REQ-082: The data model: an expert database design for every project that keeps data

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0075, SPEC-0074, SPEC-0073, SPEC-0072, SPEC-0048, SPEC-0042, SPEC-0041, SPEC-0059, ADR-0677, ADR-0675, ADR-0430, ADR-0767, ADR-0793, ADR-0794, brief #1948, brief #1919, plan #661
- Requirements: REQ-082

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-25:

> Intake for the data model on the Day-1 quality path: every project with stored data gets an expert, engine-aware database design from its domain model, curated and cited patterns and its main queries, confirmed by a person on business choices, checked offline and kept in step with each migration.

On the default branch at 1fb8181 (v0.65.1) the data model of a project is `docs/data-model.md` from
`kit/templates/data-model.md` (ADR-0677): one table of entities with three personal-data classes and a person's yes,
which `check_plan.py:contract_problems` checks only for existing. No table, column, type, constraint, index, tenancy,
audit or migration is asked for, the `migrations` gate of `config/playbooks/default.toml` is a judgement, and no step
reads a migration. SPEC-0074 now gives the domain model (`docs/domain/`) and SPEC-0073 the grill and the architecture
record's quality scenarios and threats, so the data design can be built from them rather than beside them.

## Decision

1. REQ-082 is added to `docs/requirements.md` as `planned`, and SPEC-0075 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. `docs/data-model.md` stays the one record and grows to five sections: business view, logical model, physical model
   (one subsection per store, in its engine profile's form), main queries and lifecycle. Its entities and data classes
   are read from `docs/domain/`, never retyped; `## Data stores` of the architecture record names each store's
   subsection.
3. The kit ships an engine-neutral pattern catalogue (`config/data-patterns/<topic>.toml`), each pattern cited and
   dated, and engine profiles (`config/data-engines/<family>.toml`), `relational` first; both are checked by
   `check_data_patterns.py` inside the existing `playbooks` step. The engine is read from the accepted stack option,
   never set by hand or guessed.
4. No new phase and no second interview: the grill asks the data items, the steward drafts the business and logical
   parts in planning and asks the person only the business choices, each with a recommendation; the architect writes
   the physical part in the `contract` brief or a `Kind: data-model` brief; a builder never writes the model.
5. A fresh reviewer scores the model on a fixed list kept in the catalogue and the verdict cites the score file; the
   conductor's role file and every budgeted rule file are unchanged.
6. The `data-model` and `migrations` steps of `run_gates.py` are file-only, with no network and no model; each failure
   names the rule and the path class, never an entity, a field or a value; before the record exists the step prints
   `not run`. With `[data] migrations` set the `migrations` gate is read as a check and drift between a migration and
   the model is red; unset, it stays a judgement.
7. One optional `[data]` table (`model`, `migrations`, `patterns`, `review`) holds the settings; with no table every
   result is unchanged on upgrade. `docs/domain/data.md` is the one list of data classes, and ADR-0677's three map to it
   by the person's yes.
8. The Approved specs change only by the proposals of amendments 248 (SPEC-0048 rule 10), 249 (SPEC-0072 rule 2) and
   250 (SPEC-0072 rule 5, after amendment 207), written with this intake under `docs/runs/` and each approved by the
   owner before its build.
9. This ADR names the protected class of this intake only: `docs/requirements.md`. The brief's Reserved line says the
   ADR names "the path classes of the spec, requirement and amendment proposals", but the spec (`docs/specs/`) and the
   amendment proposals (`docs/runs/`) are not protected path classes of `config/protected-paths.txt`, as ADR-0793 and
   ADR-0794 decision 9 found. Each of SPEC-0075's builds (a) to (j) changes protected classes (`config/`,
   `scripts/agk/`, `kit/`, `tests/kit/`) and decisions held elsewhere, so each writes its own ADR naming its classes.
   No build changes a workflow file (`.github/`), the ruleset, `config/reviewers.yaml` or `agk.mk`; `kit/hashes.json`
   and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec, the three amendment proposals and this ADR wait for approval.
Nothing that runs changes in this pull request: the catalogue, the profiles, the record's sections, the steps and the
settings are built by SPEC-0075's builds (a) to (j), after the amendments they depend on are approved.

## Residual

None beyond SPEC-0075's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

## Contexts

- kit: the catalogue, the engine profiles, the record's sections, the `data-model` and `migrations` steps and the `[data]` table, built by SPEC-0075's builds.
- github: the steps run inside the existing `governance` job with no workflow, ruleset, required-check or label change.
- local: the same steps run in `prepush.py` and `make -f agk.mk agk-governance`, with no recipe change.
- personal: the model in the sidecar's files, questions printed, nothing posted.
- stacks: an engine profile per store family, `relational` first, and no stack's build or test step changes.

## Open questions

`Q-S0075-1` to `Q-S0075-10` of SPEC-0075, each with its conservative reading applied in the spec's rules.

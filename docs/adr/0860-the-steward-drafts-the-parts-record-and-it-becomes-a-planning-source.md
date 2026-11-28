# ADR-0860: The steward drafts the parts record, and it becomes a planning source

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers (the owner's yes on brief #2070, 2026-11-27T19:43:41Z; amendment 258 approved on #2018,
  2026-11-27T20:04:04Z)
- Related: ADR-0834, ADR-0858, ADR-0515, ADR-0430, ADR-0748, ADR-0672, ADR-0771, SPEC-0076, SPEC-0029, SPEC-0043,
  REQ-083, brief #2070, plan #661
- Requirements: REQ-083

Protected classes: `scripts/agk/`, `kit/`, `skills/`, `.claude/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0076 (Approved, ADR-0834) rule 15 build (c) asks for the parts record's template, the steward's draft from the
needs and the health research, the person's plain questions, `plan_sources.py parts`, the planning guide step and the
stack skill's wording, and applies amendment 258 to SPEC-0029 rule 5. On main at 876c3d46 nothing wrote
`docs/parts.md`, read a health value or applied rule 6's floor; build (a) (ADR-0858) gave the `[parts]` table, the
needs catalogue and the reading order `packs.files(root, "parts")`.

## Decision

1. **The template.** `kit/templates/parts.md`: a header naming SPEC-0076, an example `## example-runtime` section with
   the rule 7 table and two invented rows (`example.com`), the `Decision: <need>: <reason>` note, `Questions for the
   person:` and the last line `Confirmed by: none yet`. `parts_record.rows(text)` reads the rows by section, so build
   (d) reads the same table.
2. **The draft.** `parts_record.py draft --proposal FILE [--root DIR] [--today YYYY-MM-DD]` reads the steward's TOML
   proposal (outside `docs/`): per need `need`, `cites` (a `REQ-…` that `docs/requirements.md` names, or
   `engineering`), `business`, an optional `runtime` and `decision`, and either `part = "stdlib"` or `[[needs.candidates]]`
   with `name`, `kind`, `version`, `released`, `licence`, `advisories`, `last_release`, `status`, `adoption`, `source`,
   `read` and optional `scorecard`, `commercial` and `service`. One section per runtime of the Accepted stack record
   (`pins.chosen_parts`; a runtime is a `pins.STACKS` name, else the first part). `Why` and `Alternatives considered`
   come from the stack catalogue (`config/parts/<STACKS folder>.toml`, project row first, then the kit's, then a pack's),
   else `catalogue: none`. The first candidate that meets the floor is kept: its licence passes `licences.passes` on
   `licences.allowed_list`, its last release within `parts.max_age_months`, no advisory at the `parts.advisories`
   level, neither `deprecated` nor `archived`. It writes `docs/parts.md` once, records `Setup: parts: drafted <n> needs,
   <q> questions because ...` through `steward.record` and prints each question.
3. **The questions.** Only rule 7's four kinds, each one sentence that passes `steward_owner.question_problem`: a paid
   or commercial licence (`LicenseRef-*` or `commercial = true`), a licence off the list, an outside service that costs
   money or sends data out (`service`), and a need with no healthy candidate. The steward asks each with `ask`.
4. **Refusals.** Exit 1, writing and recording nothing, naming the rule and the key, never a value: a refused
   `[parts]` table, no work type (`delivery.work_type`), no Accepted stack record, an existing record, a proposal that
   is not TOML or is under `docs/`, a health value with no recorded `Setup: web-research: yes` (`Q-2070-1`), an unknown
   need, a cite that is neither, a missing, unknown or wrong key, a date after `--today`, and a second part for one
   need with no `decision`.
5. **The planning source.** `plan_sources.py parts` writes once `docs/sources/parts.md` (`Source: parts record`,
   `Kind: other`, `Version: parts <digest>`, `Date:`) with the record unchanged; it refuses a missing record, one
   whose last `Confirmed by:` is missing or `none yet`, and an existing target.
6. **The path.** `docs/guides/planning.md` gains step 4a and names `plan_sources.py parts` in step 6;
   `skills/stack/SKILL.md` names the platform only in `Parts:`; `.claude/agents/steward.md` names the draft after the
   stack; amendment 258 item 1 is applied to SPEC-0029 rule 5 word for word. `stack-check` gains no refusal.

## Consequences

A library reaches `docs/parts.md` only from a proposal whose health was read on the person's recorded research yes and
met the floor, with its need cited. No check, workflow or governance step changes; both commands read files only.

## Residual

The `parts` gate and the `check_plan.py` hold are build (d); the build files written from the record are build (e);
the harvest of `inferred` rows is build (g).

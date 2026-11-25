# ADR-0793: Add REQ-080: Every idea is grilled before its vision and held to industry practice from day 1

- Status: Proposed
- Date: 2026-11-24
- Deciders: maintainers
- Related: SPEC-0073, SPEC-0037, SPEC-0038, SPEC-0047, SPEC-0048, SPEC-0059, SPEC-0062, SPEC-0063, SPEC-0072, ADR-0075, ADR-0386, ADR-0643, brief #1915, brief #1400, brief #1381, brief #1918, plan #661
- Requirements: REQ-080

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-24:

> Intake for Day-1 quality: a grill interview tests every idea before its vision, and the same path then holds the product, design, architecture and build to industry practice, in solo and team, with no slower path and no new CI job.

The brief is issue #1918, under plan #661. On the default branch at d18e46bd (v0.65.1) discovery is a form: `/agk:vision`
asks the ten topics and the playbook's `[[discovery]]` questions once each, only `scale` carries a recommendation, and no
question asks for the evidence of the problem, what users do today, the riskiest assumption, a failure story or a reason
to stop; nothing pushes back on a vague answer. The discovery check is closed over `front_door.ORDER`, and the
architecture record's held set `NEW_SECTIONS` exempts only a record with none of its sections, so neither can take a new
id or section without failing every record already written. No spec, skill, playbook, role file or guide names a
pre-mortem, a glossary, a threat model or STRIDE.

## Decision

1. REQ-080 is added to `docs/requirements.md` as `planned`, and SPEC-0073 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. Every problem is grilled in discovery before its vision: rounds of at most three questions, each with a recommended
   answer drawn from what the steward read; the items are `[[discovery]]` entries of the playbooks with `depth` and
   `critical` keys, kept outside `ORDER` so every existing record passes unchanged.
3. The answer is always the person's: a recommendation becomes an answer only on the plain yes to that one question in
   solo mode and the reviewer's own words in team mode; nothing is settled by evidence in planning.
4. A design whose discovery has a `## Readiness` section with a critical item open and no accepted risk is held by
   `check_design.py`, an existing governance step, while `[quality] grill_hold` is true; a document without the section
   is never held.
5. Five quality layers enter records that exist: alternatives in the research record, one product glossary, a usability
   and WCAG check for screens, quality scenarios, threats and operations in the architecture record under their own hold,
   and the test design rules, the refactor step, two review axes and one weekly survey metric.
6. One optional `[quality]` table holds the settings; no table means every default and no `agk.toml` change on upgrade.
7. No new phase, workflow, CI job, required check, role, judgement gate, `agk.mk` recipe or `governance_map.CHECKS` step;
   no budgeted rule file grows.
8. The Approved specs change only by the proposals of amendments 235 (SPEC-0048), 236 (SPEC-0072), 237 (SPEC-0038,
   SPEC-0037), 238 (SPEC-0063) and 239 (SPEC-0047), written with this intake under `docs/runs/` and each approved by
   the owner before its build.
9. This ADR names the protected class of this intake only: `docs/requirements.md`. The spec (`docs/specs/`) and the
   amendment proposals (`docs/runs/`) are not protected path classes of `config/protected-paths.txt`. Each of SPEC-0073's
   builds (a) to (j) changes protected classes (`config/`, `scripts/agk/`, `skills/`, `kit/`, `tests/kit/`,
   `tests/kit_dev/`) and decisions held elsewhere, so each writes its own ADR naming its classes. No build changes a
   workflow file (`.github/`), the ruleset, `config/reviewers.yaml` or `agk.mk`; `kit/hashes.json` and the version stay
   the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec, the five amendment proposals and this ADR wait for approval. Nothing
that runs changes in this pull request: the grill, its records, the hold, the quality layers and the settings are built
by SPEC-0073's builds (a) to (j), after the amendments they depend on are approved.

## Residual

None beyond SPEC-0073's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

## Contexts

- kit: a skill, an installed script, two playbook keys, a settings table and file-only checks in existing governance steps, built by SPEC-0073's builds.
- github: the checks run inside the existing `governance` job; no workflow, ruleset, required-check or label change.
- local: the same checks in `prepush.py` and `make -f agk.mk agk-governance`, with no recipe change.
- personal: printed and written in the sidecar, nothing posted.
- stacks: no stack's build or test step changes.

## Open questions

`Q-S0073-1` to `Q-S0073-11` of SPEC-0073, each with its conservative reading applied in the spec's rules.

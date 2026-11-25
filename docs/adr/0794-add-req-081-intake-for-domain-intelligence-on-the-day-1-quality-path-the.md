# ADR-0794: Add REQ-081: The Day-1 quality path knows the customer's domain

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0074, SPEC-0073, SPEC-0038, SPEC-0042, SPEC-0048, SPEC-0057, SPEC-0059, SPEC-0062, SPEC-0072, ADR-0735, ADR-0793, brief #1400, brief #1381, brief #1918, brief #1919, plan #661
- Requirements: REQ-081

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-25:

> Intake for domain intelligence on the Day-1 quality path: the grill, the glossary, the architecture and review know the customer's business, its rules and its regulations, from cited domain packs and the project's own domain model, confirmed by a person where it matters.

The brief is issue #1919, under plan #661; it replaces the parked #1400. On the default branch at d36d2bb (v0.65.1)
nothing in the kit knows a business domain: `ls config/domains` fails, and no file names a regulation's jurisdiction,
a retention period, a four-eyes rule or a business rule id. SPEC-0073 (#1918) now holds the one interview (the grill),
the one glossary and the architecture record's quality scenarios and threats, so #1400's own interview, glossary and
conductor lens no longer fit the path as built.

## Decision

1. REQ-081 is added to `docs/requirements.md` as `planned`, and SPEC-0074 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. The kit ships a domain pack format (`config/domains/<slug>.toml`), its check and two seed packs, never one for every
   domain; a project derives its own pack from cited research and promotes it only by SPEC-0048 rule 24's evidence path.
3. Packs compose once, after `default`, the work type and its modules, a stronger gate replacing a weaker and a
   weakening refused; the stricter of two regulations holds until a person decides.
4. Domain items join the grill of SPEC-0073 and its readiness; domain terms join its one glossary; domain constraints
   become rows of its quality scenarios. No second interview, glossary or review lens.
5. The project domain model lives in `docs/domain/` with business rules `BR-<n>`, each sourced, owned and confirmed or
   inferred; a brief's `Rules:` line is checked by `check_brief.py`; review uses checklist items 1 and 8 reworded within
   their word counts, and `.claude/agents/conductor.md` is unchanged.
6. A person confirms regulations, money and safety rules and the data classification; the steward never states that a
   product complies. One optional `[domain]` table holds the settings; no table means no pack and no `agk.toml` change.
7. No new phase, workflow, CI job, required check, role, `agk.mk` recipe or `governance_map.CHECKS` step; no budgeted
   rule file grows.
8. The Approved specs change only by the proposals of amendments 240 (SPEC-0048 rule 23) and 241 (SPEC-0072 rule 5),
   written with this intake under `docs/runs/` and each approved by the owner before its build.
9. This ADR names the protected class of this intake only: `docs/requirements.md`. The brief's Reserved line says the
   ADR names "the path classes of the spec, requirement and amendment proposals", but the spec (`docs/specs/`) and the
   amendment proposals (`docs/runs/`) are not protected path classes of `config/protected-paths.txt`, as ADR-0793
   decision 9 found for SPEC-0073. Each of SPEC-0074's builds (a) to (h) changes protected classes (`config/`,
   `scripts/agk/`, `skills/`, `kit/`, `tests/kit/`, `tests/kit_dev/`) and decisions held elsewhere, so each writes its
   own ADR naming its classes. No build changes a workflow file (`.github/`), the ruleset, `config/reviewers.yaml` or
   `agk.mk`; `kit/hashes.json` and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec, the two amendment proposals and this ADR wait for approval. Nothing
that runs changes in this pull request: the packs, their check, the composition, the domain model, the `Rules:` line
and the settings are built by SPEC-0074's builds (a) to (h), after the amendments they depend on are approved.

## Residual

None beyond SPEC-0074's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

## Contexts

- kit: the pack format and its check, two seed packs, composition, the grill's items, the domain model and the `Rules:` line, built by SPEC-0074's builds.
- github: the checks run inside the existing `governance` job with no workflow, ruleset, required-check or label change.
- local: the same checks run in `prepush.py` and `make -f agk.mk agk-governance`, with no recipe change.
- personal: the packs and the domain model in the sidecar's files, nothing posted.
- stacks: synthetic test data follows the packs' shapes, and no stack's build or test step changes.

## Open questions

`Q-S0074-1` to `Q-S0074-9` of SPEC-0074, each with its conservative reading applied in the
spec's rules.

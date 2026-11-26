# ADR-0834: Add REQ-083: The parts list: every library chosen for a need, with its reason, kept in step

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: SPEC-0076, SPEC-0075, SPEC-0074, SPEC-0072, SPEC-0054, SPEC-0041, SPEC-0029, SPEC-0011, ADR-0430, ADR-0671, ADR-0672, ADR-0676, ADR-0748, ADR-0800, ADR-0807, brief #2017, plan #661
- Requirements: REQ-083

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-26:

> Intake for the parts list: after the stack is accepted and before the foundation, each library a product uses is chosen per need from a cited catalogue, recorded with its reason, alternatives and health, explained in plain words, and kept in step with every build file and lock.

On the default branch at 425701d5 (v0.65.1) a product's libraries are named per stack option in the stack record's
`Parts:` (SPEC-0029 rule 5), with no need, reason, alternative or health per library; the build-file templates start
empty (`"dependencies": {}`, `dependencies = []`) and grow by whichever builder adds an import; `pins.py` passes a direct
dependency that the stack record never names, and `licences.py` and the bill (SPEC-0054) read licences and advisories but
not why a library is there.

## Decision

1. REQ-083 is added to `docs/requirements.md` as `planned`, and SPEC-0076 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. One record, `docs/parts.md`, holds the libraries, one row per need with its reason, alternatives, licence, health
   and one business sentence; the stack record keeps the platform only (runtime, framework, database engine, hosting).
   The build files and locks are written from the record and checked against it.
3. The step sits in the `stack and technical design` stage, after the stack is accepted and before the planning
   sources and the foundation; no new stage and no second interview.
4. The kit ships a needs catalogue (`config/parts/needs.toml`) and one maintainers' catalogue per stack
   (`config/parts/<stack>.toml`, `node` and `python-pyproject` first), each row cited and dated and holding no version;
   both are checked by `check_parts_catalogue.py` inside the existing `playbooks` step.
5. A part's health is read once at choice time with the person's research permission and recorded with its source and
   date; every check reads only the recorded values, never the network and never a model.
6. The person is asked only a paid licence, an off-list licence, an outside service that costs money or sends data out,
   and a need with no healthy candidate; the rest is the architect's, reviewed by a fresh reviewer with the bundle only.
7. A new file-only `parts` step of `run_gates.py` fails a dependency the record does not name, a record part missing
   from a build file, a version out of step, an empty required column and a second part for one need with no
   `Decision:`, naming the rule and the component class, never a name or a version.
8. One optional `[parts]` table (`record`, `max_age_months`, `advisories`) holds the settings; with no table every result
   is unchanged on upgrade.
9. The Approved specs change only by the proposals of amendments 258 (SPEC-0029 rule 5), 259 (SPEC-0072 rule 4) and 260
   (SPEC-0054 rules 2 and 3), written with this intake under `docs/runs/` and each approved by the owner before its
   build.
10. This ADR names the protected class of this intake only: `docs/requirements.md`. The brief's Reserved line says the
   ADR names "the path classes of the spec, requirement and amendment proposals", but the spec (`docs/specs/`) and the
   amendment proposals (`docs/runs/`) are not protected path classes of `config/protected-paths.txt`, as ADR-0807
   decision 9 found. Each of SPEC-0076's builds (a) to (i) changes protected classes and decisions held elsewhere, so
   each writes its own ADR naming its classes. No build changes a workflow file (`.github/`), the ruleset,
   `config/reviewers.yaml` or `agk.mk`; `kit/hashes.json` and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec, the three amendment proposals and this ADR wait for approval.
Nothing that runs changes in this pull request: the catalogues, the record, the step and the settings are built by
SPEC-0076's builds (a) to (i), after the amendments they depend on are approved.

## Residual

None beyond SPEC-0076's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

## Contexts

- kit: the needs and stack catalogues, the parts record, the `parts` step and the `[parts]` table, built by SPEC-0076's builds.
- github: the step runs inside the existing `governance` job with no workflow, ruleset, required-check or label change.
- local: the same step runs in `prepush.py` and `make -f agk.mk agk-governance`, with no recipe change.
- personal: the record in the sidecar's files, questions printed, nothing posted.
- stacks: one catalogue and one lock reader per stack, `node` and `python-pyproject` first.

## Open questions

`Q-S0076-1` to `Q-S0076-12` of SPEC-0076, each with its conservative reading applied in the spec's rules.

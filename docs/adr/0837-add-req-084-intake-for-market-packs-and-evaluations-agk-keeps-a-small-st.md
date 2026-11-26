# ADR-0837: Add REQ-084: Market packs and evaluations: pinned, scanned, dated packs, promoted by evals

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: SPEC-0077, SPEC-0029, SPEC-0041, SPEC-0045, SPEC-0048, SPEC-0054, SPEC-0066, SPEC-0071, SPEC-0073, SPEC-0074, SPEC-0075, SPEC-0076, ADR-0171, ADR-0430, ADR-0807, brief #2022, brief #2020, brief #2017, brief #1381, plan #661
- Requirements: REQ-084

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-26:

> Intake for market packs and evaluations: AGK keeps a small stable core and reads its stack, language, library, domain and pattern knowledge, and its skills, from pinned, scanned, dated packs, and promotes a pack or a release only when reference products score as well or better.

On the default branch at c34d84e (v0.65.1) the kit's knowledge is data, but bound to the kit: playbooks, domain packs,
standards, stack defaults, stack and domain signals and the licence template are files under `config/` and `kit/`, all of
the `protected` class, so each change is a kit release. Only playbooks and domain packs read a project's own file first;
the other four kinds are read from the kit alone. Only domain packs and derived playbooks carry a source and a date. An
`[engines]` skill from any plugin but `agk` is reported `plugin-unreadable` by `doctor.py`, and nothing pins or hashes an
outside skill, plugin or documentation server. No reference product or evaluation exists; the v1 run (#1772) scored the
three pilots "Not ready".

## Decision

1. REQ-084 is added to `docs/requirements.md` as `planned`, and SPEC-0077 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. The kit splits into a core, changed only by release, and knowledge in nine kinds read from packs. Today's files stay
   where they are as the built-in pack `agk-core`, so with no `[packs]` table every result is unchanged on upgrade.
3. A pack is a folder or a marketplace plugin with one `agk-pack.toml` (id, exact version, publisher, tier, licence,
   source, kit range, dates, kinds, each file's SHA-256, permissions), checked offline by `check_packs.py` inside the
   existing `playbooks` step.
4. A project pins its packs in `[packs] use` and `config/packs.lock` in ADR-0171's form, a version and a hash checked on
   every use; `packs.py add` and `update --check` read the network only on the person's recorded yes, and `verify` runs
   offline inside the `playbooks` step. Adding or changing a pack is a protected change with an ADR in the project.
5. One resolver reads `agk-core`, then the packs in order, then the project's own files; composition never weakens a gate,
   a floor or an approval, and the stricter regulation holds until a person decides.
6. A pack carries knowledge and skills only. It passes the secret, outbound, instruction, licence and size scans before
   anything is written; a pack skill is an engine and never decides. Current facts are read at the moment of choice
   through recorded research or a declared read-only documentation server, and checks read only the recorded values.
7. Kit-only evaluations on invented reference products, three runs each, scored by a fresh reviewer against a rubric and
   costed per accepted feature, are the bar: a pack, a release or a tier mapping is promoted only by an eval record the
   person accepted. Evals use a model, so they never run in CI or a required check.
8. One optional `[packs]` table (`use`, `trust`, `stale_months`, `mcp`) holds the settings, each refused by name.
9. The Approved specs change only by the proposals of amendments 261 (SPEC-0029 rules 1 and 2) and 262 (SPEC-0074 rules 3
   and 12), written with this intake under `docs/runs/` and each approved by the owner before its build.
10. This ADR names the protected class of this intake only: `docs/requirements.md`. The brief's Reserved line says the ADR
    names "the path classes of the spec, requirement and amendment proposals", but `docs/specs/` and `docs/runs/` are not
    paths of `config/protected-paths.txt` (`docs/specs/` is the `architecture` class of `config/reviewers.yaml`, which the
    protected-change check does not read for this), as ADR-0807 decision 9 found. Each of SPEC-0077's builds (a) to (j)
    changes protected classes (`config/`, `scripts/agk/`, `kit/`, `tests/kit/`, `.claude-plugin/`) and writes its own
    ADR naming them. No build changes a workflow file (`.github/`), the ruleset, `config/reviewers.yaml` or `agk.mk`;
    `kit/hashes.json` and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec, the two amendment proposals and this ADR wait for approval. Nothing
that runs changes in this pull request: the format, the resolver, the lock, the scans, the settings and the evals are built
by SPEC-0077's builds (a) to (j), after the amendments they depend on are approved.

## Residual

None beyond SPEC-0077's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

## Contexts

- kit: the pack format, the resolver, the lock, the scans and the evals, built by SPEC-0077's builds, with `evals/` kit-only.
- github: the pack checks run inside the existing `governance` job's `playbooks` step with no workflow, ruleset, required-check or label change.
- local: the same checks run in `prepush.py` and `make -f agk.mk agk-governance`, with no recipe change.
- personal: packs are pinned in the sidecar, and evals run over the sidecar's files with nothing posted.
- stacks: each stack's knowledge arrives as a pack, and the core keeps no stack beyond `agk-core`.

## Open questions

`Q-S0077-1` to `Q-S0077-13` of SPEC-0077, each with its conservative reading applied in the spec's rules.

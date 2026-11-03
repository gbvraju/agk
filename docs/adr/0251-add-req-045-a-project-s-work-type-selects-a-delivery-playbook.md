# ADR-0251: Add REQ-045: A project's work type selects a delivery playbook that never weakens a gate

- Status: Accepted
- Date: 2026-11-02
- Deciders: maintainers
- Related: SPEC-0038, SPEC-0034, SPEC-0037, REQ-020
- Requirements: REQ-045

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-02:

> A project declares its work type and the kit applies that type's delivery playbook, so each kind of work (web, mobile, cloud migration, RAG, MCP, multi-agent, voice) is built along its fastest proven path while every governance gate stays as it is.

The plan is issue #499 and the brief is issue #500. The owner set the direction in plan #499,
dated there 2026-11-03: "adopt faster delivery strategy... it should work greatly", for the seven
work types the plan lists. It is recorded as one row of `docs/runs/decisions-log.md`, dated by
`date -u` (`Q-S0038-12`). Today the kit runs one flow for every project, and the only place the
kind of work shows up is the stack ADR. In the pilot's Phase 2 a hand-designed strategy cut the
critical path (contract first with mocks, a per-module `[testing]` map, milestone pull requests,
lock slots and joins ordered by demo value), and nothing in the kit chose it. The pilot's data is
private: this ADR and the spec describe only the strategy's shape, and a run record that later
turns a web-app claim into `measured` holds only timings, counts and that shape, with no project
name, no organisation, no people, no screen or feature names and no data from the pilot, and
invented names only (`example.com`); the review of the pull request that adds it checks this
(SPEC-0038 rule 11).

## Decision

1. REQ-045 is added to `docs/requirements.md` as `planned`. SPEC-0038 is added as `Draft`. Merging
   this pull request approves the requirement as a proposal; it does not approve the spec, which
   stays `Draft` until the person's own `Approve:` line approves it (SPEC-0032 rule 5).
2. A playbook is data, one TOML file per work type; it can make delivery faster (order, lanes,
   test suggestions, batching, milestone shape) and only adds gates of its work type, never
   removing, skipping or relaxing one (SPEC-0038 rules 1 to 4). The owner chooses the work type
   by the `[delivery] work_type` line of `agk.toml`, which lands only with an ADR; a session never
   writes it, and a project without it runs exactly as today (rule 5).
3. The builds of SPEC-0038 rule 12 will change these protected path classes: `config/` (the
   playbooks under `config/playbooks/`), `scripts/agk/` (`playbook.py`, `check_playbooks.py`,
   `doctor.py`, `engines.py` and `session_plan.py`), `kit/` (`kit/manifest.json` and the
   `[delivery]` table of `kit/templates/agk.toml`), `agk.mk` (one governance step), `agk.toml`
   (the commented `[delivery]` table of this repository, which declares no work type), `skills/`
   (`skills/stack/SKILL.md` and `skills/brief/SKILL.md`), `.claude/` (`.claude/agents/conductor.md`,
   the `Playbook evidence:` line), and `tests/kit/` and `tests/kit_dev/` (their tests). Each build
   adds its own ADR naming the classes it changes and citing this one, because the protected-path
   check counts only an ADR added or changed in the same pull request (`Q-S0038-9`). No build
   changes `.github/`, `constitution/`, `CLAUDE.md`, `Makefile`, `pyproject.toml` or
   `.claude-plugin/`.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done. No check, flow or setting changes in
this pull request, and a project that declares no work type sees no change from any build.

## Residual

None. The intake checks cannot tell whether the criteria, the gates per work type or the speed
claims are the right ones; that is the review of this pull request.

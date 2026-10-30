# ADR-0204: Add REQ-044: A design phase delivers a click-through prototype that sign-off freezes

- Status: Proposed
- Date: 2026-10-30
- Deciders: maintainers
- Related: SPEC-0037, SPEC-0029, REQ-036
- Requirements: REQ-044

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-10-30:

> A project's design phase delivers a click-through prototype for demos and sign-off, built on a modern default UX standard the kit ships, covering every screen and state of the spec; the person's sign-off freezes one version, and every UI build is held to it.

The plan is issue #365 and the brief is issue #366. The person ruled the three questions of #365 on
2026-10-30 (the conductor's field note on #365), choosing the proposals: the kit's own hashed,
offline navigation runtime; a structural match within a small pixel tolerance, with drift named in
the verdict and judged by the conductor, never failed automatically; and v1 regenerated from the
inventory, carrying the theme over. The rulings are rows of `docs/runs/decisions-log.md`.

## Decision

1. REQ-044 is added to `docs/requirements.md` as `planned`. SPEC-0037 is added as `Draft`. Merging
   this pull request approves the requirement as a proposal; it does not approve the spec, which
   stays `Draft` until the person's own `Approve:` line approves it (SPEC-0032 rule 5).
2. The spec amends REQ-036 AC5 to AC7 by its rules 5 and 12 (the no-script rule allows exactly the
   kit's hashed runtime in a prototype version folder; the design folder becomes
   `docs/design/prototype/<version>/`; existing mockup folders still read as before). The text of
   REQ-036 is not edited here, because an intake only adds to the requirements file.
3. The builds of SPEC-0037 rule 14 will change these protected path classes: `kit/` (the standard,
   the patterns, the inventory, prototype and sign-off templates, the runtime, the fixture set,
   `kit/manifest.json` and the `[design]` table of `kit/templates/agk.toml`), `scripts/agk/` (the
   design scripts and checks, `check_final_clearance.py`, `session.py` and `doctor.py`), `skills/`
   (`skills/design/SKILL.md`), `tests/kit/` and `tests/kit_dev/` (their tests), `config/`
   (`config/session-rules.md`, where the `Approve: design` line lives) and `.claude/`
   (`.claude/agents/conductor.md`, the verdict that names drift). Each build adds its own ADR naming
   the classes it changes and citing this one, because the protected-path check counts only an ADR
   added or changed in the same pull request (`Q-S0037-9`). No build changes `.github/`,
   `constitution/`, `CLAUDE.md`, `Makefile`, `agk.mk`, `agk.toml` of this repository or
   `pyproject.toml`.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval in the weekly
report. Nothing is delivered until the requirement is done. Existing mockup folders and
`/agk:design <name>` keep working, so no project is broken by the builds.

## Residual

None. The intake checks cannot tell whether the criteria are the right ones; that is the review of
this pull request.

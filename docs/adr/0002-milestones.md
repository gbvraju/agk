# ADR-0002: Milestones

- Status: Accepted
- Date: 2026-10-14
- Deciders: maintainers
- Related: ADR-0001
- Requirements: REQ-009, REQ-010, REQ-011, REQ-012

## Context

The kit is delivered in stages so that each stage is proven before the next builds on it.

## Decision

- K0 — self-governed skeleton: repository layout, requirements, ADR-0001/0002, checks with tests, CI governance
  job, reviewer-group model, PR template, briefs template, build-state. Exit: `make governance` green on the kit
  itself; PR #1 merged under the rules it introduces.
- K1 — install into a new repository: `agk init` (a script, later a plugin command) creates the layout, checks,
  CI job and branch-rule instructions in an empty repository. Exit: proven on a throwaway repository with a
  two-item brief.
- K2 — install into an existing repository: `agk adopt` merges without touching product code; idempotent.
  Includes the reviewer agent (spec-vs-diff) and the drift audit workflow. Exit: proven on a real codebase.
- K3 — plugin and metrics: Claude Code plugin packaging (`/agk:init`, `/agk:brief`, `/agk:review`,
  `/agk:doctor`), per-PR metrics recorded in the PR body and aggregated weekly; optional adopted components
  behind profile flags.
- Repository public from K0 (2026-10-14, reason: CI minutes on a private plan); K4 = public launch: docs site, handbook, profiles, licence review of adopted components.

Non-goals for v0: other agents or hosts; Jira/Linear; hosted services; UI.

## Consequences

Work is sequenced by milestone; a requirement is planned against the milestone named in its title.

## Residual

- 2026-10-14: exit criteria for K3 and K4 are stated at the level of the brief and need measurable thresholds
  before those milestones start.

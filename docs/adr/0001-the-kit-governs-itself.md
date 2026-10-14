# ADR-0001: The kit governs itself

- Status: Accepted
- Date: 2026-10-14
- Deciders: maintainers
- Related: ADR-0002
- Requirements: REQ-001, REQ-002, REQ-003

## Context

agk exists so that agent output stays consistent. A kit that asks others to adopt rules it does not follow
cannot be trusted. Every rule it ships therefore applies to this repository from PR #1.

## Decision

1. Layout: `constitution/` (vision, principles), `config/` (reviewers, protected paths, neutrality tokens),
   `docs/` (requirements, ADRs, specs, briefs, runs, build-state), `scripts/agk/` (checks), `tests/kit/` (tests of
   the checks), `.claude/` (settings, hooks, agents), `.github/` (workflow, PR template).
2. Protected paths are listed in `config/protected-paths.txt`: `constitution/`, `config/`, `.claude/`, `.github/`,
   `docs/requirements.md`. They change only with a new or modified ADR in the same PR. A change that touches only
   `- Status:` lines of `docs/requirements.md` is exempt.
3. The one direct push to `main` is the repository creation commit (README and LICENSE). Everything else goes
   through a pull request that passes the `governance` job.
4. Checks live in `scripts/agk/`, use the standard library only, make no network calls, and are exercised by
   tests in `tests/kit/`. `make governance` runs them; `make test` runs the tests.
5. Reviewer model: path classes map to reviewer groups in `config/reviewers.yaml`; approvers are teams, never
   personal names. Agents implement; maintainers decide.
6. This PR creates the protected paths and is covered by this ADR.

## Consequences

- Weakening a check requires an ADR, which makes the weakening visible and reviewable.
- Bootstrapping requires one-time exceptions: the build-state file is created in the PR that adds the check
  guarding it.

## Residual

- 2026-10-14: branch protection and required-review settings are GitHub settings, not files; they are documented
  and verified by `agk doctor` in a later milestone (REQ-002 AC1).

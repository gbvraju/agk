# ADR-0578: Add REQ-072: One command sets up any machine as a ready, correctly sized AI workforce

- Status: Accepted
- Date: 2026-11-16
- Deciders: maintainers
- Related: SPEC-0065, SPEC-0005, SPEC-0041, SPEC-0059, SPEC-0061, SPEC-0062, SPEC-0063, SPEC-0064, ADR-0577, brief #1376, brief #1378, plan #661
- Requirements: REQ-072

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-16:

> Intake for /agk:setup: one command turns any machine, Windows, WSL 2 or a cloud machine, into a ready and correctly sized AI workforce for one project, so business users get it from the steward by asking and developers by running it once.

The brief is issue #1378, under plan #661. On the default branch at 9454566 the kit installs into a repository
(`/agk:init`, `/agk:adopt`), checks a machine (`/agk:doctor`), upgrades by pull request (`/agk:upgrade`), starts
builders on a yes (`/agk:launch`) and moves a Windows workforce into WSL 2 (`/agk:wsl`, ADR-0577), but no command takes a
new machine from nothing to a working workforce: a first-time person must know the tools, their versions, the plugin,
the folder trust, the sign-ins and the settings. Every setting the brief names lives in `agk.toml`, a protected path.

## Decision

1. REQ-072 is added to `docs/requirements.md` as `planned`, and SPEC-0065 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. One plugin skill, `/agk:setup`, with `status` and `back`, run by a person or by the steward on a person's plain
   request, reads the machine and the repository first, asks only what it cannot read, shows one plan and acts on one
   yes; its machine work is kit-only scripts run from the plugin root, never installed into a project, as `/agk:wsl` is.
3. Machine settings (the scheduler task, the folder trust) are applied after the yes; project settings (`execution`,
   `review_mode`, `max_builders`, `builder_memory_gb`, `launch_adapter`, `[autopilot]`) are only proposed, as a change
   with its own ADR that the person commits and pushes and the owner merges (SPEC-0005 rule 8).
4. In a team the roles of each machine are read from the repository: never a second live conductor, never a steward for
   a login that is not a listed reviewer, and the conductor only for a login whose lease and verdicts the kit counts
   (`verdict_authors`); the builders stay within `max_builders` across the team.
5. `/agk:wsl` becomes the WSL path and stays callable on its own; `/agk:init`, `/agk:adopt`, `/agk:doctor`,
   `/agk:upgrade` and `/agk:launch` are called, never copied.
6. This ADR names the protected class of this intake only. Builds (b) (the project-settings ADR it proposes in a
   project) and (g) (`.claude/agents/steward.md`) change decisions held elsewhere, so each writes its own ADR. Builds (a),
   (c), (d), (e), (f) and (h) will change `skills/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `kit/` (the kit-only
   list of `kit/manifest.json`) and `agk.toml` (`[[testing.map]]` entries only); each may cite this ADR with
   `Covered-by: ADR-0578` once it is Accepted only if it changes no other class and no decision named here (session rule
   36). No build changes a workflow file (`.github/`), the ruleset or `config/reviewers.yaml`; `kit/hashes.json` and the
   version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request: the command and its scripts are built by SPEC-0065's builds (a) to (h).

## Residual

None beyond SPEC-0065's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

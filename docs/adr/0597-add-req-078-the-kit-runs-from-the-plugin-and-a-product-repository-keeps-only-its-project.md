# ADR-0597: Add REQ-078: The kit runs from the plugin and a product repository keeps only its project

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers
- Related: SPEC-0071, SPEC-0041, SPEC-0059, SPEC-0061, SPEC-0064, SPEC-0028, ADR-0203, brief #348, brief #1419, brief #1420, plan #661
- Requirements: REQ-078

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-16:

> Intake for a clean product repository: the whole kit runs from the AGK plugin on the machine, the repository keeps only the project's own records, and one command removes AGK at the end of an engagement, with the workforce's speed, quality and cost unchanged.

The brief is issue #1420, under plan #661. On the default branch at 01b619e, an installed project holds the 146 verbatim
kit files of `kit/manifest.json` (93 scripts, 8 workflows, 10 playbooks, 6 agents, 5 hooks, the governance rules, the
guides and the templates), and its prompts, agents, hooks, guards and gate call them as `python3 scripts/agk/...` inside
the project, so anyone who clones the project can copy the kit. The kit-only scripts already run from the plugin as
`${CLAUDE_PLUGIN_ROOT}/scripts/agk/...`. Personal mode (SPEC-0041) keeps the kit out of the product but has no
workforce. `uninstall.py` (brief #348, ADR-0203) already removes the released kit files and keeps the project's work.

## Decision

1. REQ-078 is added to `docs/requirements.md` as `planned`, and SPEC-0071 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. In a clean project the whole kit runs from the plugin installed at user scope, and the repository keeps only the
   project's own records, a short `CLAUDE.md`, `LICENSE-AGK` and the files that git and GitHub read only from the
   repository; the workforce (conductor, builders, steward, autopilot, claims, reviews and the guarded merge) works
   exactly as in local mode.
3. A clean project requires `execution = "local"`. CI mode keeps today's install until a separate design is approved;
   personal mode is unchanged.
4. `[kit] plugin_version` in `agk.toml` pins the plugin version; every session refuses a mismatch or a missing plugin,
   naming the setting.
5. The move in is `/agk:upgrade --clean-repo`, one pull request that is reverted by reverting it; the move out is
   `/agk:uninstall`, extended, which keeps the specs and decisions by default and prints, never runs, the history
   clean-up. The kit never force-pushes or rewrites history.
6. No customer project is migrated before SPEC-0071's rehearsal shows the clean run within 10% of the installed run on
   lead time, tokens per merged pull request, first-review pass rate and failed checks.
7. This ADR names the protected classes of this intake only. Builds (a), (b), (c) and (f) change decisions held elsewhere
   (the session prompts and the session rules that name a script, `.claude/` and `.claude-plugin/`, the `[kit]` table of
   `agk.toml`, the steward's role file), so each writes its own ADR. Builds (d), (e) and (g) will change `scripts/agk/`,
   `tests/kit/`, `tests/kit_dev/`, `skills/` and `kit/`; each may cite this ADR with `Covered-by: ADR-0597` once it is
   Accepted only if it changes no other class and no decision named here (session rule 36). No build changes a workflow
   file (`.github/`), the ruleset or `config/reviewers.yaml`; `kit/hashes.json` and the version stay the release's
   (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request: the resolver, the pin, the migration, the uninstall and the rehearsal are built by SPEC-0071's builds (a) to (g).

## Residual

None beyond SPEC-0071's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

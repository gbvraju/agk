# ADR-0580: Add REQ-073: Plain claude opens the steward and every session the kit starts names its role

- Status: Accepted
- Date: 2026-11-16
- Deciders: maintainers
- Related: SPEC-0066, SPEC-0041, SPEC-0059, SPEC-0061, SPEC-0062, SPEC-0063, SPEC-0064, SPEC-0065, SPEC-0071, ADR-0559, ADR-0578, brief #1378, brief #1380, brief #1381, brief #1382, plan #661
- Requirements: REQ-073

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-16:

> Intake for AGK's front door: after installing AGK, a person who types claude is met by the steward, sees only a few plainly named commands, and is guided from there, while every session the kit starts still runs as its own role.

The brief is issue #1380, under plan #661. On the default branch at 460c788 the `agk` plugin shows all 24 of its skills
in the `/` menu, ships no agent and no `settings.json` of its own, and a project's `.claude/settings.json` (a `verbatim`
file of `kit/manifest.json`) sets no `agent`. Plain `claude` in an AGK project opens a default session that may answer
without the steward's evidence order, memory or guard. Both launch adapters run `claude <flags> -p <prompt>` with no
`--agent`, although `launch.py` and `conductor.py` already pass `AGK_AGENT` for role and reviewer starts, so a session
the kit starts runs as a default session that reads its role file, and that role's guard in the agent's front matter
does not run for it. A default agent set before every kit start names its agent would turn each such start into the
steward.

## Decision

1. REQ-073 is added to `docs/requirements.md` as `planned`, and SPEC-0066 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. Every session the kit starts names its agent (`--agent` from `AGK_AGENT`), and a test fails on a kit start of
   `claude` that names none; a `builder` agent file is added from SPEC-0061 rule 7. This ships in a release before any
   default agent is set, never in the same one.
3. Inside an AGK project the steward always answers: `init`, `adopt` and `upgrade` set `agent` to the steward in the
   project's own settings, never in the kit's own repository, and keep a project's own different value. The steward goes
   on only on the default branch, up to date, or in its own worktree, and otherwise stops with one line and the fix.
4. With the `agk` plugin enabled, plain `claude` outside an AGK project opens the plugin's steward, which writes nothing
   without the person's yes; the first run greets a person who has nothing set up in at most three plain lines.
5. The `agk` plugin's menu shows exactly `/agk:status`, `/agk:help` and `/agk:upgrade`; every other skill is hidden, keeps
   its name and is run by the steward on a plain request; a developer plugin that depends on `agk`, offered to team
   setups (brief #1381), shows every skill again and sets no default agent.
6. This ADR names the protected class of this intake only. Builds (a) (the adapters, `launch.py`, the runtime templates
   and a new agent file), (d) (`.claude/settings.json` and its manifest entry, the plugin's settings and agent, the
   steward's role file) and (e) (the steward's role file) change decisions held elsewhere or protected classes this ADR
   does not name, so each writes its own ADR. Builds (b), (c) and (f) will change `skills/`, `.claude-plugin/`, `tests/kit/`,
   `tests/kit_dev/`, `docs/guides/` and `README.md`; each may cite this ADR with `Covered-by: ADR-0580` once it is Accepted
   only if it changes no other class and no decision named here (session rule 36). No build changes a workflow file
   (`.github/`), the ruleset or `config/reviewers.yaml`; `kit/hashes.json` and the version stay the release's (session
   rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request: the settings, the agents, the menu and the first run are built by SPEC-0066's builds (a) to (f), in the release
order of its rule 11.

## Residual

None beyond SPEC-0066's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

# ADR-0552: Add REQ-068: A teammate joins as a builder in one command and leaves cleanly

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0061, SPEC-0012, SPEC-0034, SPEC-0041, SPEC-0045, SPEC-0058, ADR-0368, ADR-0402, ADR-0438, ADR-0487, ADR-0536, ADR-0543, brief #1306, plan #661
- Requirements: REQ-068

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-14:

> Intake for a standalone builder: one command a teammate runs on their own laptop joins the team, gets work from the one conductor, builds each brief in a short session on the right model, and leaves cleanly, so any number of teammates can join or leave at any time.

The brief is issue #1306, under plan #661. Builders today are numbered slots `s1` to `s<n>` of a fixed count
(`builder_slots`, by default `max_builders`), started by the conductor's adapter or by hand. A slot's marker counts only by a
login in `verdict_authors`, so a teammate with their own login cannot hold one. No agent file wraps a builder's rules. In
local mode the conductor checks a builder's evidence record from a folder on its own machine, which another laptop never
shares. One evening of a customer project showed long builder sessions growing context for hours, a session opened in the
main folder confusing the conductor (#1301), and every start and stop needing the owner.

## Decision

1. REQ-068 is added to `docs/requirements.md` as `planned`, and SPEC-0061 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until the owner's own `Approve:` line approves it.
2. A teammate joins with one command, `builder.py --name <member>`, a loop with no model that joins, requests, builds,
   reports and leaves, and starts one `claude --agent builder` session per brief on the tier of the brief's kind
   (SPEC-0061 rules 2, 6 and 7).
3. A member slot is a new slot name form; its count is the members present, not a setting, and the conductor's capacity
   is the live member slots plus its own adapter builders under `max_builders` as a ceiling (rules 3, 4 and 9).
4. The one conductor assigns: members post `Request:` and act on `Assign:` lines whatever `[flow] assign` says, and a
   departed member's brief is reassigned on the same pull request (rule 5, `Q-S0061-4`).
5. Members may build but never decide: their slot, request, take, report and question lines count, and verdict,
   assignment, approval and answer lines stay limited to the configured people (rule 8).
6. In local mode a member's evidence record also travels as a git ref, `refs/agk/evidence/<head>`, holding no secret and
   checked by the conductor's sample rerun; that build waits for the owner's ruling on pushing such a ref (rule 10,
   `Q-S0061-6`).
7. This is the one ADR of REQ-068 for the builds of SPEC-0061 rule 15, for what it names here. They will change these
   protected path classes: `scripts/agk/` (`builder.py`, `session.py`, `launch.py`, `evidence.py`), `.claude/` (the
   builder and conductor agents), `skills/` (the `builder` skill), `kit/` (the manifest entries and the adapters),
   `tests/kit/`, `tests/kit_dev/` (the install test of the new files), `agk.toml` (the `[[testing.map]]` entries and, by
   the owner's choice, the `[team]` table) and `config/` (`session-rules.md`, `core-rules.md` and `rule-budget.txt`). A
   build that changes a class named here and no other may cite this ADR with `Covered-by: ADR-0552` once it is Accepted
   (session rule 36), unless it changes a decision of an Approved spec or of an ADR, as builds (b) and (c) do for session
   rule 18 and the conductor's text, which then write their own. No build changes a workflow file (`.github/`), the
   ruleset, `constitution/` or `config/reviewers.yaml`; `kit/hashes.json` and the version stay the release's (session
   rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request, and until the builds land, builders start and are cleared as they are now.

## Residual

None beyond SPEC-0061's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

# ADR-0389: Add REQ-065: A light dispatcher does the mechanical work and AI runs as short jobs per item

- Status: Proposed
- Date: 2026-11-09
- Deciders: maintainers
- Related: SPEC-0058, SPEC-0012, SPEC-0030, SPEC-0032, SPEC-0034, SPEC-0039, SPEC-0045, SPEC-0049, ADR-0330, ADR-0353, ADR-0354, ADR-0368, brief #855, plan #661
- Requirements: REQ-065

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-09:

> Intake for a live conductor without long sessions: a light dispatcher with no AI and flat memory reads GitHub in near real time and does all mechanical work, and the conductor's judgment runs as short AI jobs, one per item, on the right model, the same locally, on WSL and in the cloud.

The brief is issue #855, under plan #661. The conductor today is a long scheduled session with a watch loop. Labels,
merges and stall detection wait for whichever session is awake, a dead holder keeps its lease for up to 10 minutes,
GitHub drops most scheduled sweeps, and a person cannot tell whether a session is working. What the brief builds on is
not all on the default branch: the states, action table and board of #846, the capacity table of #842 and the usage
reader of #798 are open, and the relay is four scheduled tasks of one account, not a file of the kit.

## Decision

1. REQ-065 is added to `docs/requirements.md` as `planned`, and SPEC-0058 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until the owner's own `Approve:` line approves it.
2. A small program of the kit, `dispatcher.py`, standard library and kit modules only and no model, does the mechanical
   work of each pass, and is off unless `[dispatch] enabled = true` (SPEC-0058 rules 2 to 5).
3. Merging from the dispatcher is a separate setting, off by default, and only ever runs `merge_cleared.py`. Principle 2
   names the conductor alone and ADR-0354 records that its text lags the merger job, so turning this on is the owner's
   ruling of `Q-S0058-5` (rule 6).
4. One dispatcher per repository is held by the existing GitHub lease as well as a lock on the machine, because a lock
   cannot see a second machine (rule 8).
5. Judgment runs as short jobs, one per item, started by the dispatcher on the kind's tier with a wall-clock limit and a
   token cap, from a prompt holding only kit text and numbers. No AI session runs a watch loop (rules 9 to 11).
6. In the cloud nothing is added to the router and merger, and jobs start from scheduled tasks per tier. A GitHub event
   cannot start a cloud session, and a session's start of another session has been refused; both are stated as limits,
   and a refused start is listed as stuck (rule 12).
7. The dispatcher replaces the conductor's watch loop, the relay as the normal route and the lease's renew loop only for
   a repository that turns it on and only once the build that does it lands, each by that build's own change to the
   Approved texts (rule 15).
8. This is the one ADR of REQ-065 for the builds of SPEC-0058 rule 18, for what it names here. They will change these
   protected path classes: `scripts/agk/`, `kit/` (the manifest entry and the service templates), `tests/kit/`,
   `tests/kit_dev/` (the install test of the new files), `agk.toml` (the `[[testing.map]]` entries and, by the owner's
   choice, the table), `.claude/` (the conductor's instructions) and `config/` (`session-rules.md`, `core-rules.md` and
   `rule-budget.txt`). A build that changes a class named here and no other may cite this ADR with
   `Covered-by: ADR-0389` once it is Accepted (session rule 36), unless it changes a decision of an Approved spec or of an
   ADR, as rule 15 requires of builds (b) and (c), which then write their own. No build changes a workflow file
   (`.github/`), the ruleset, `constitution/` or `config/reviewers.yaml`; `kit/hashes.json` and the version stay the
   release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request, and until the builds land and a repository sets `enabled = true`, the conductor, the relay and the lease work as
they do now. A repository that turns it on needs one machine that stays awake, and spends tokens only on jobs that have
an item.

## Residual

None beyond SPEC-0058's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

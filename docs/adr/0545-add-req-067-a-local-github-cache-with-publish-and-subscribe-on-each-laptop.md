# ADR-0545: Add REQ-067: A local GitHub cache with publish and subscribe on each laptop, nothing hosted

- Status: Accepted
- Date: 2026-11-15
- Deciders: maintainers
- Related: SPEC-0060, SPEC-0012, SPEC-0030, SPEC-0041, SPEC-0058, ADR-0191, ADR-0295, ADR-0529, ADR-0536, ADR-0548, ADR-0565, brief #1284, brief #1262, brief #1251, plan #661
- Requirements: REQ-067

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-15:

> Intake for a local GitHub cache with publish and subscribe on each laptop: one publisher per clone reads only what changed with free conditional requests, every session reads the cache and is woken by changes, and nothing is hosted.

The brief is issue #1284, under plan #661. Every session of the kit reads GitHub itself: each waiting builder re-reads
its pull request and the `agk-conductor` issue on its own timer, and the planner, the router, the conductor, the steward
and the board each make their own reads. Brief #1251 (ADR-0529, ADR-0548) made each read cheaper with ETags, `since=`
and a per-repository JSON cache in the temp folder, but each session still asks on its own. The organisation has blocked
GitHub Actions minutes, a webhook needs an address that a laptop does not have, and GitHub's own webhook forwarding is
for testing and allows one forwarder per repository. The owner asked for something simple that hosts nothing.

## Decision

1. REQ-067 is added to `docs/requirements.md` as `planned`, and SPEC-0060 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until the owner's own `Approve:` line approves it.
2. Each clone keeps one SQLite cache file under its git common directory, shared by its worktrees, never tracked and
   rebuilt in full when it is deleted or its schema changes (SPEC-0060 rule 2).
3. One publisher per clone, held by a lease, makes only the repository-wide conditional delta reads every
   `[cache] poll_seconds`, heals with an hourly catch-up, writes the cache and appends one line per change to a local
   change log (rules 3 and 4).
4. Every reader reads the cache first and GitHub only when the cache is missing, its publisher is not live or its data
   is older than `[cache] max_age_seconds`; a waiting session is woken by a change log line instead of its own poll,
   and falls back to today's wait when no publisher runs (rules 5 and 6).
5. GitHub stays the one source of truth: every write goes to GitHub, and only its reply is written to the cache
   (rule 7). Each laptop runs its own publisher; nothing is shared between laptops and nothing is hosted, and no
   webhook, workflow or Actions job is added in any mode (rules 9 and 12).
6. This is the one ADR of REQ-067 for the builds of SPEC-0060 rule 14, for what it names here. They will change these
   protected path classes: `scripts/agk/` (a new `cache.py`, and `session.py`, `session_plan.py`, `route.py`,
   `conductor.py`, `steward.py`, `board.py`, `config.py`), `.claude/` (the conductor's report line and start of the
   publisher, and its guard's allowance of `session.py cache --status`), `kit/` (the manifest entry of the new
   script), `tests/kit/`, `tests/kit_dev/` (the install test of the new file), `agk.toml` (the `[cache]` table and the
   `[[testing.map]]` entry) and `config/` (session rule 10's text on what ends a wait, when build (c) changes it). A
   build that changes a class named here and no other may cite this ADR with `Covered-by: ADR-0545` once it is Accepted
   (session rule 36), unless it changes a decision of an Approved spec or of an ADR, as build (b) does for ADR-0548's
   read cache and build (c) for session rule 10, which then write their own. No build changes a workflow file
   (`.github/`), the ruleset, `constitution/` or `config/reviewers.yaml`, and no build changes SPEC-0058;
   `kit/hashes.json` and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request, and until the builds land, every session reads GitHub as it does now.

## Residual

None beyond SPEC-0060's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

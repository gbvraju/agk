# ADR-0360: Add REQ-062: The right tests for each stack, run at the right time by a map that learns

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: SPEC-0055, SPEC-0012, SPEC-0021, SPEC-0038, SPEC-0039, SPEC-0041, SPEC-0044, SPEC-0046, SPEC-0047, ADR-0242, ADR-0323, ADR-0359, plan #661
- Requirements: REQ-062

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-08:

> Intake for project testing by stack: a project's front end, back end, mobile and other parts each run the right tests at the right time, a pull request runs only what its change can break, and AGK learns from every test the selection missed.

The brief is issue #774, under plan #661. The kit selects tests by rule (`scripts/agk/impact.py`,
ADR-0220) and runs them through `[proof]` areas, but an area has one command and no levels, the map
is written by hand, a data file with no entry makes a pull request's run full (measured in
SPEC-0055), and timing, rerun and quarantine lean on pytest's output. The owner asked that the
difference between AGK itself and AGK in a project be found and remembered. The brief names REQ-051
as the home of this spec, unless the spec shows it does not cover it: REQ-051's six criteria are
about timing, workers, the after-merge smoke run and a folder scan, and none reads on levels, a
generated map, links across areas, a full run by mode or a map that learns. REQ-062 is therefore
new.

## Decision

1. REQ-062 is added to `docs/requirements.md` as `planned`, and SPEC-0055 as `Draft`. Merging this
   pull request approves the requirement as a proposal; the spec stays `Draft` until the owner's
   own `Approve:` line approves it. REQ-051 and SPEC-0044 do not change.
2. There is one mechanism and two sources of data: AGK itself has one area and a curated map, a
   project has areas with levels and a generated map that learns. The difference is one setting,
   `[testing] map_source`, and no script has a path of its own for the kit (SPEC-0055 rule 1).
3. A generated map is never committed (principle 5); only learned entries, which cannot be derived,
   are committed, to `docs/runs/test-links.toml`, and they only ever add tests (SPEC-0055 rules 5
   and 12).
4. The full suite stays where it is in GitHub mode; local and personal mode run it before the merge
   and once a day, so a project without CI still has a full run (SPEC-0055 rule 10).
5. This is the one ADR of REQ-062 for the builds of SPEC-0055 rule 15, except build (b), which is
   brief #773 with ADR-0359. They will change these protected path classes: `scripts/agk/`,
   `tests/kit/`, `kit/` (the new script's entry in `kit/manifest.json` and the ignore line of
   `kit/templates/gitignore`) and `agk.toml` (the `map_source` line and one `[[testing.map]]` entry
   per new script). A build that changes a class named here and no other may cite this ADR with
   `Covered-by: ADR-0360` once it is Accepted (session rule 36). A workflow file (`.github/`) is out
   of scope: a build that needs one writes its own ADR with the owner's yes quoted in its brief. No
   build changes `constitution/`, `config/`, `.claude/`, `CLAUDE.md`, `Makefile`, `agk.mk`,
   `pyproject.toml`, `skills/`, `.claude-plugin/` or `tests/kit_dev/`; `kit/hashes.json` and the
   version stay the release's (session rule 14).
6. Three Approved specs are not edited here. Build (g) proposes an amendment of SPEC-0039 rule 6;
   build (j) proposes one of SPEC-0047 if a scorecard metric is wanted; a report of a `nightly`
   failure would need one of SPEC-0046 rule 1 and is listed as a residual of SPEC-0055.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs
changes in this pull request; until build (a) lands a `[proof]` area has no levels, and until build
(c) lands no map is generated.

## Residual

None beyond SPEC-0055's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.

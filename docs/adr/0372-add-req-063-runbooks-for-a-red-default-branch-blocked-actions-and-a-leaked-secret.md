# ADR-0372: Add REQ-063: Runbooks for a red default branch, blocked Actions and a leaked secret

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: SPEC-0056, SPEC-0009, SPEC-0011, SPEC-0012, SPEC-0021, SPEC-0032, SPEC-0041, SPEC-0042, SPEC-0046, SPEC-0047, plan #661
- Requirements: REQ-063

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-08:

> Intake for runbooks: when the default branch goes red, GitHub Actions minutes run out or a secret leaks, a person has one short checked page of steps, and the time to restore is measured (plan #661 phase 7, tracker #630 row 10).

The brief is issue #789, under plan #661. The pieces exist but no page joins them: the issue `The
default branch is red`, the fix record, the local-mode guide, `minutes.py` and the secret scan. For
a leak, nothing tells a person what to do first, and no record exists from which a time could be
read. The local-mode guide, which `minutes.py` names, is not installed in a project, and the weekly
product report holds neither a time to restore nor the run minutes.

## Decision

1. REQ-063 is added to `docs/requirements.md` as `planned`, and SPEC-0056 as `Draft`. Merging this
   pull request approves the requirement as a proposal; the spec stays `Draft` until the owner's
   own `Approve:` line approves it.
2. There are three pages, one each, under `docs/runbooks/`, installed verbatim for AGK itself and
   every project with the local-mode guide they link to, and they repeat none of what they link to
   (SPEC-0056 rules 2 to 4).
3. A new installed check holds each page to its form and each command it names to something that
   exists, reading and never running them, with no network (rules 5 and 6). No page gives a command
   whose output can hold a value (rule 7).
4. For a leak, a person revokes the credential first, and history is not rewritten and no ignore
   list grows (rule 10). One issue opened after revocation, with two times and a label and nothing
   else, is the record the time is read from (rule 11).
5. The product report prints the time to restore of the three kinds and the run minutes, counts and
   timings only, `unknown` and never 0 for what cannot be read (rule 12).
6. This is the one ADR of REQ-063 for the builds of SPEC-0056 rule 15. They will change these
   protected path classes: `scripts/agk/`, `tests/kit/`, `kit/` (the manifest entries and
   `kit/facts-schema.json`), `agk.mk` (the governance step), `agk.toml` (one `[[testing.map]]`
   entry for the new script) and `tests/kit_dev/` (the facts wiring test of build (d)). A build
   that changes a class named here and no other may cite this ADR with `Covered-by: ADR-0372` once
   it is Accepted (session rule 36). No build changes a workflow file (`.github/`), the ruleset,
   `constitution/`, `config/`, `.claude/`, `CLAUDE.md`, `Makefile`, `pyproject.toml`, `skills/` or
   `.claude-plugin/`; `kit/hashes.json` and the version stay the release's (session rule 14).
7. Three Approved specs are not edited here. Build (c) proposes an amendment of SPEC-0032 rule 7,
   and build (d) amendments of SPEC-0009 rules 3, 15 and 19 and SPEC-0011 rules 2 and 10.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs
changes in this pull request; until the builds land, there are no pages and the report is as it is.

## Residual

None beyond SPEC-0056's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.

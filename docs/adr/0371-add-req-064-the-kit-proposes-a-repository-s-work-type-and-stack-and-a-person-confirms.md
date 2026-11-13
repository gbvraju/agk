# ADR-0371: Add REQ-064: The kit proposes a repository's work type and stack and a person confirms

- Status: Accepted
- Date: 2026-11-08
- Deciders: maintainers
- Related: SPEC-0057, SPEC-0002, SPEC-0012, SPEC-0021, SPEC-0038, SPEC-0041, SPEC-0048, SPEC-0055, plan #661
- Requirements: REQ-064

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-08:

> Intake for stack detection: AGK reads an existing repository's lockfiles and manifests and proposes its work type and stack for a person to confirm, and never decides them (plan #661 phase 3, edge case 8).

The brief is issue #790, under plan #661. A repository brought to AGK mid-life already says much about itself in
its lockfiles and manifests, and today nothing reads them to help a person: discovery starts from an empty
`Work type` guess, and SPEC-0055 rule 13 names a detection that does not exist. The two things the brief reuses are
not both available: `adopt.detect_tests` knows Python only and is not installed in a project, and the survey of
SPEC-0041 is not built. The declaration of a work type is the owner's and must stay so.

## Decision

1. REQ-064 is added to `docs/requirements.md` as `planned`, and SPEC-0057 as `Draft`. Merging this
   pull request approves the requirement as a proposal; the spec stays `Draft` until the owner's
   own `Approve:` line approves it.
2. `front_door.py detect` reads a repository at its head and prints a proposed work type and stack,
   each with the file that suggests it. It writes nothing and has no option that decides. Mixed or
   absent signals are said plainly, and no candidate is ranked (SPEC-0057 rules 2 to 4).
3. One data file, `config/stack-signals.toml`, read from the kit's own root, holds every signal, and
   a form check holds it to the playbooks that exist. The playbook format gains no key (rule 5).
4. The read is the head commit's files that the table names, as text by line patterns. It runs,
   imports, installs and fetches nothing (rules 6 and 7).
5. `adopt.detect_tests` and the survey are reused with no second copy: until the survey is built
   the first is used, its fallback answer is not a signal, and where it cannot be loaded the line
   says `not read` (rule 8).
6. The person's answer in discovery is what sets the document's `Work type`, and the declaration
   stays the owner's (rule 9).
7. This is the one ADR of REQ-064 for the builds of SPEC-0057 rule 14. They will change these
   protected path classes: `scripts/agk/`, `config/` (the new table only), `kit/` (its manifest
   entry), `tests/kit/`, `tests/kit_dev/` (the install test of the table), `agk.toml` (the
   `[[testing.map]]` entry) and `skills/` (the step of `/agk:vision`). A build that changes a class
   named here and no other may cite this ADR with `Covered-by: ADR-0371` once it is Accepted
   (session rule 36). No build changes a workflow file (`.github/`), the ruleset, `constitution/`,
   `config/reviewers.yaml`, `.claude/`, `CLAUDE.md`, `Makefile`, `pyproject.toml`, `agk.mk` or
   `.claude-plugin/`; `kit/hashes.json` and the version stay the release's (session rule 14).
8. No Approved spec is edited here. Build (d) proposes an amendment only if the one list of
   SPEC-0057 rule 8 needs a change to SPEC-0041.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs
changes in this pull request; until the builds land, discovery and `/agk:stack` work as they do now.

## Residual

None beyond SPEC-0057's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.

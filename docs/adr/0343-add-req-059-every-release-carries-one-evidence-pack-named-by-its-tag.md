# ADR-0343: Add REQ-059: Every release carries one evidence pack, named by its tag

- Status: Accepted
- Date: 2026-11-08
- Deciders: maintainers
- Related: SPEC-0052, SPEC-0012, SPEC-0028, SPEC-0046, SPEC-0047, ADR-0171, ADR-0326, ADR-0328, plan #661, issues #433 and #476
- Requirements: REQ-059

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-08:

> Intake for the evidence pack: every release carries one folder, named by its tag, that holds its tests, scans, coverage, software bill of materials and decisions (plan #661 phase 7, wave 4).

The brief is issue #737, filed under plan #661 phase 7, whose gap closed reads, quoted as data:
"a tag that is not a release is caught (#433, #476 class) by the pack check". Issues #433 and #476
are open: the tags v0.62.0 and v0.63.0 were pushed on commits whose `agk.toml` states another
version, and nothing records what a release shipped with.

What exists and is reused (SPEC-0052 rule 1): the release by tag and its test (`check_tag.py`,
SPEC-0028), the required check `governance` and its pinned secret scan, the pinned CI tools
(`config/ci-tools.txt`), the coverage figure of the weekly drift audit, the scorecard's readers and
weekly section (SPEC-0047) and the failure record (SPEC-0046). What is missing: one place that
holds, per release, what was checked and with what; and no dependency scanner exists at all.

## Decision

1. REQ-059 is added to `docs/requirements.md` as `planned`, and SPEC-0052 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it.
2. The pack is one folder `<out>/<tag>/` of five JSON parts and one index of their digests, made
   by the read-only `release_pack.py make` (GET only, posts nothing) into a folder outside the
   repository or git-ignored, never committed (principle 5) and never uploaded (SPEC-0052 rules 2
   and 3).
3. The release test is `check_tag.failure` on the tagged commit, so a tag of the #433 and #476
   class gets no pack and is refused again by the check; a repository without the kit's release
   files has no release test yet and is refused naming the path class (SPEC-0052 rule 4).
4. Unknown is never passed and never 0: a check, a scan, a count or a figure that cannot be read
   is `unknown`, and a scan that nothing configures is `not run` (SPEC-0052 rules 5 to 7).
5. The bill of materials is read from the repository's files at the tag, in the kit's own JSON;
   a standard format and a required dependency scanner are left to the supply-chain intake of
   plan #661 phase 7 (SPEC-0052 rules 6 and 8).
6. The pack check is offline and refuses a missing, extra, malformed or altered part, a part with
   a data-guard finding and a tag that is not a release, naming the part and never a value; a
   failed or unknown check or scan is a `warn pack:` line, not a refusal (SPEC-0052 rule 10).
7. This is the one ADR of REQ-059 for the builds of SPEC-0052 rule 12. The builds will change
   these protected path classes: `scripts/agk/` (`release_pack.py`, builds (b) to (d)),
   `tests/kit/` (`test_release_pack.py`), `kit/` (the new installed script's entry in
   `kit/manifest.json`, build (b)) and `agk.toml` (its one `[[testing.map]]` entry, build (b)). A
   build that changes a class named here and no other may cite this ADR with
   `Covered-by: ADR-0343` once it is Accepted (session rule 36). No build changes
   `constitution/`, `config/` (the kit-only list does not grow), `config/reviewers.yaml`, a
   workflow, the ruleset (`kit/templates/ruleset.json`), `.github/CODEOWNERS`, `CLAUDE.md`,
   `Makefile`, `agk.mk`, `pyproject.toml`, `skills/` or `.claude-plugin/`; `kit/hashes.json` and
   the version stay the release's (session rule 14). Running `make` from the tag workflow, or
   attaching a pack to a release, is a later change with its own ADR and the owner's yes.

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request; until build (b) lands no pack can be made or checked, and
issues #433 and #476 stay as they are, for a person.

## Residual

None beyond SPEC-0052's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.

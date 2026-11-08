# ADR-0349: Add REQ-061: Every dependency is scanned and listed in a standard bill of materials

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: SPEC-0054, SPEC-0012, SPEC-0047, SPEC-0052, ADR-0171, ADR-0326, ADR-0328, ADR-0343, plan #661
- Requirements: REQ-061

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-08:

> Intake for supply-chain security: every dependency and pinned tool of the kit is scanned for known weaknesses and listed in a standard bill of materials, offline in checks, with the result in each release's evidence pack (plan #661 phase 7).

The brief is issue #741, filed under plan #661 phase 7. The kit pins its CI test tools
(`config/ci-tools.txt`, ADR-0328), its secret scanner (ADR-0171) and every action by commit SHA,
but nothing lists them in a standard form and nothing checks them for known weaknesses: no
dependency scanner is configured anywhere (SPEC-0052 rule 1, measured again in SPEC-0054 rule 1).
The evidence pack of SPEC-0052 (Draft, ADR-0343 Proposed) leaves the bill's standard format and the
scanner to this intake (`Q-S0052-8`, `Q-S0052-10`).

## Decision

1. REQ-061 is added to `docs/requirements.md` as `planned`, and SPEC-0054 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it.
2. The bill is a CycloneDX 1.6 JSON document of the components the repository's files declare
   (Python requirements, CI tools, pinned scanners, actions and, in the kit, installed files), made
   from files at a commit with no network call, the same bytes for the same commit; a requirement
   that is not pinned exactly is listed as `unpinned`, never with a guessed version (SPEC-0054
   rules 2 and 3).
3. `sbom.py check` is offline and refuses a bill that does not match its commit, naming the
   component class and never a value; no governance step runs it in these builds (SPEC-0054
   rule 4).
4. The scanner (OSV-Scanner, pinned by version and archive digest) and its database are read only
   by a workflow step of its own that the owner approves, never by a check; a finding opens or
   edits one issue labelled `agk-supply-chain` with counts and ids only and blocks nothing until the
   owner rules a threshold by ADR (SPEC-0054 rules 6 to 8).
5. The evidence pack's `bom.json` becomes this bill and its dependency scan entry names this
   scanner, once the maintainers approve a patch to SPEC-0052 rules 6 and 8; until the scan step
   exists the entry stays `not run` (SPEC-0054 rule 5).
6. This is the one ADR of REQ-061 for builds (b), (c) and (e) of SPEC-0054 rule 10. They will
   change these protected path classes: `scripts/agk/` (`sbom.py`, and `release_pack.py` in build
   (e)), `tests/kit/` (`test_sbom.py`, `test_release_pack.py`), `kit/` (the new installed script's
   entry in `kit/manifest.json`, build (b)) and `agk.toml` (its one `[[testing.map]]` entry, build
   (b)). A build that changes a class named here and no other may cite this ADR with
   `Covered-by: ADR-0349` once it is Accepted (session rule 36). Build (d) changes `.github/` (a
   workflow) and writes its own ADR with the owner's yes quoted in its brief. No build changes
   `constitution/`, `config/` (`config/ci-tools.txt` and the kit-only list stay as they are),
   `config/reviewers.yaml`, the ruleset (`kit/templates/ruleset.json`), `.github/CODEOWNERS`,
   `CLAUDE.md`, `Makefile`, `agk.mk`, `pyproject.toml`, `skills/` or `.claude-plugin/`;
   `kit/hashes.json` and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request; until build (b) lands no bill can be made or checked, and until
build (d) lands with the owner's yes nothing scans the components.

## Residual

None beyond SPEC-0054's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.

# ADR-0595: Add REQ-077: A locked release is cut on its own branch while all work keeps merging

- Status: Proposed
- Date: 2026-11-18
- Deciders: maintainers
- Related: SPEC-0070, SPEC-0028, SPEC-0031, SPEC-0039, SPEC-0041, SPEC-0051, SPEC-0052, SPEC-0069, ADR-0108, brief #1418, plan #661
- Requirements: REQ-077

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-18:

> Intake for locked releases: the owner locks a release's scope once, builders keep merging everything to the default branch, and the release is cut on its own branch from the commit where the locked scope is complete, so a release never chases a moving branch, in every mode.

The brief is issue #1418, under plan #661. On the default branch at 4babb36, a release is one pull request into the
default branch that gathers every fragment under `changelog.d/`, raises the three versions, regenerates
`kit/hashes.json` and accepts the pending ADRs (SPEC-0028 rule 4, ADR-0108); when the default branch moves, the release
pull request merges it, gathers again and regenerates the hashes again (release brief #1384, answer 2). Nothing separates
what is built from what is planned for a release, and there is no lock, no release branch, no backport and no merge-back.

## Decision

1. REQ-077 is added to `docs/requirements.md` as `planned`, and SPEC-0070 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. Build all, release what is locked: a release is a milestone `Release <version>`; the owner locks its list once with
   `Lock: <version>` and changes it only with `Lock: <version> add #n` or `drop #n`; every brief is still built and
   merged to the default branch.
3. When the last locked item has merged, `release/<version>` is made from the first default-branch commit that holds every
   locked item (the cut), recorded as `Cut: <version> <sha>`. The release pull request targets that branch, gathers only
   the fragments present at the cut and never merges the default branch again. Only a backport the owner approves with
   `Backport: #n` enters the branch after the cut.
4. The owner merges the release pull request and tags `v<version>` on the release branch, as today; one generated
   merge-back pull request then brings the changelog section, the versions and the hashes to the default branch and
   removes only the released fragments; the release branch is deleted after it.
5. No session merges, tags, pushes a `release/*` branch or deletes one (session rules 2 and 22): the kit prints those
   steps and the owner, or the person in personal mode, runs them (SPEC-0070 `Q-S0070-2`).
6. This ADR names the protected classes of this intake only. Builds (a) to (f) will change `scripts/agk/`, `tests/kit/`,
   `tests/kit_dev/`, `kit/` and `docs/guides/`; each may cite this ADR with `Covered-by: ADR-0595` once it is Accepted
   only if it changes no other class and no decision named here (session rule 36). A build that changes
   `constitution/principles.md`, `CLAUDE.md`, `config/session-rules.md`, `config/reviewers.yaml`, `agk.toml` (the
   `[release] max_hours` setting) or amends SPEC-0028 writes its own ADR; principle 3's "branched from the default
   branch" is amended that way before a release or backport pull request into `release/*` is built (`Q-S0070-3`). No
   build of this intake changes a workflow file (`.github/`) or the ruleset (`kit/templates/ruleset.json`); protecting
   `release/*` is a repository rule the owner sets. `kit/hashes.json` and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request: the lock, the cut, the release pull request into `release/*`, the backports, the merge-back and personal mode are
built by SPEC-0070's builds (a) to (f).

## Residual

None beyond SPEC-0070's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

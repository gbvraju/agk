# ADR-0567: Add REQ-070: In team mode every listed reviewer may run a steward, first come first served

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: SPEC-0063, SPEC-0059, SPEC-0062, SPEC-0039, ADR-0541, ADR-0546, ADR-0556, brief #1320, brief #1318, brief #1342, plan #661
- Requirements: REQ-070

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-15:

> Intake for the steward in team mode: every listed reviewer may run a steward on their own machine, stewards take questions first come first served, and each relays only the words of the reviewer signed in on that machine, recorded under that reviewer's GitHub login.

The brief is issue #1342, under plan #661. SPEC-0059 (Approved, ADR-0541) assumes one owner and one login: one steward
per project, no lease, and a relay marked `Who: ProductOwner`. SPEC-0062 (Approved, ADR-0556) holds only in solo mode and
leaves the decider in team mode open (`Q-S0062-3`). On the default branch at f17f56b, `steward.py` refuses a second
start while any other session's `Started: steward` is live, whoever posted it, and its roll-over is not guarded against
two stewards reaching 500 comments at once. With two reviewers each starting a steward on their own machine, both may
answer the same `Question:` and both may roll the memory issue over.

## Decision

1. REQ-070 is added to `docs/requirements.md` as `planned`, and SPEC-0063 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. SPEC-0063 holds only in team mode (`review_mode = "team"`); in solo mode SPEC-0062 holds unchanged, and in personal
   mode SPEC-0059 rule 14 holds.
3. In team mode "the owner" is any listed reviewer, as the kit's readers list them (`verdict_authors` or the team
   `maintainers`' user handle, and `spec_approvers`; a team handle lists nobody). A steward starts only when the login
   `gh` is signed in with on its machine is listed, read once with `gh api user` and kept for the run; otherwise it
   prints one line naming the file and the settings, never the login, and stops. Several reviewers may each run one;
   a second live start of the same login stands by.
4. A steward takes a question with one `Taking: Q-<id> <login> <UTC time>` comment and a re-read; the earliest by
   GitHub's comment order holds it, a later one withdraws, a `Taking:` lapses after `[flow] owner_wait_minutes`, and a
   posted answer ends the question for all. The memory roll-over and the daily list are done once, after a
   `Taking: rollover` or `Taking: daily <date>`.
5. A relay carries only the words the signed-in reviewer typed in its own chat, with SPEC-0059 rule 5's quote and a last
   line `Who: <login>`; every decision line in team mode names the login, `ProductOwner` stays the solo value and the
   steward's own lines keep `Who: AGK steward`.
6. A steward may post `Approve:` in team mode only on its own reviewer's plain yes, only when that login is in
   `spec_approvers` and only for that login; `Confirmed:`, `Verdict:`, `Final:` and `Correction:` stay denied, and merges,
   tags, force pushes and workflow changes stay the person's or denied.
7. This ADR names the protected classes of this intake only. Build (a) changes `config/` (session rule 17 gains the place
   of `Taking:`) and build (c) changes ADR-0546 decision 4 (the readers count a `Who: <login>` approval), so each writes
   its own ADR. Build (b) will change `.claude/` (the steward's agent file), `scripts/agk/` (the relay and the record),
   `tests/kit/`, `tests/kit_dev/` and `kit/` (the manifest); it may cite this ADR with `Covered-by: ADR-0567` once it is
   Accepted only if it changes no other class and no decision named here (session rule 36). No build changes a workflow
   file (`.github/`), the ruleset or `config/reviewers.yaml`; `kit/hashes.json` and the version stay the release's
   (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request: the team clauses are built by SPEC-0063's builds (a) to (c).

## Residual

None beyond SPEC-0063's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

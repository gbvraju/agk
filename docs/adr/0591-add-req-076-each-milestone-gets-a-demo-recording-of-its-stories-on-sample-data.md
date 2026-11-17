# ADR-0591: Add REQ-076: Each milestone gets a demo recording of its stories on sample data

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers
- Related: SPEC-0069, SPEC-0043, SPEC-0051, SPEC-0042, SPEC-0041, SPEC-0059, brief #1402, plan #661
- Requirements: REQ-076

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-16:

> Intake for the milestone demo recording: when a milestone's last user story is built, a builder records an automated walkthrough of the milestone's stories on sample data, and the recording is attached to the milestone before its release.

The brief is issue #1402, under plan #661. On the default branch at c4a7605, a milestone closes on test records and
verdicts: the plan writes a `Demo:` line naming each milestone's screens (SPEC-0043 build (r)), the `web-app` playbook has
an `e2e-smoke` gate, the `pilot` playbook a scripted demo, and SPEC-0051's acceptance record takes a `demo` evidence item
under `docs/runs/`, but nothing records something a person can watch.

## Decision

1. REQ-076 is added to `docs/requirements.md` as `planned`, and SPEC-0069 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until a spec approver's own `Approve:` line approves it.
2. One demo brief per milestone with something to show, keyed `demo`, after the milestone's last story briefs; its
   walkthrough is an ordinary test under `tests/demo/<milestone>/` that captions each story and runs on seeded synthetic
   data only; the recording's form follows the kind of product (video, screen recording, transcript or run record).
3. A recording is never committed: it is a release asset or a run artifact in CI mode, an asset the builder uploads to an
   existing release in local mode, and a file under `~/.agk` in personal mode; the committed index
   `docs/demos/<milestone>.md` names the head, the date, the captions, the length, the size and where it is.
4. The demo is evidence for the steward's sign-off question and SPEC-0051's acceptance record, never an approval.
   `[demo] mode`, `max_minutes` and `max_mb` set it, and refusals name the setting, never a value.
5. This ADR names the protected classes of this intake only. Builds (a) to (e) will change `scripts/agk/`, `tests/kit/`,
   `tests/kit_dev/` and `kit/`; each may cite this ADR with `Covered-by: ADR-0591` once it is Accepted only if it
   changes no other class and no decision named here (session rule 36). A build that adds the `[demo]` table to
   `agk.toml`, changes a playbook in `config/`, changes `.claude/agents/steward.md` or amends SPEC-0051 writes its own
   ADR. No build of this intake changes a workflow file (`.github/`), the ruleset or `config/reviewers.yaml`;
   `kit/hashes.json` and the version stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request: the demo brief, the walkthrough, the storage and the index are built by SPEC-0069's builds (a) to (e).

## Residual

None beyond SPEC-0069's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

# ADR-0541: Add REQ-066: A steward answers what the evidence settles and asks the owner only the rest

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0059, SPEC-0012, SPEC-0037, SPEC-0041, SPEC-0042, SPEC-0043, SPEC-0045, ADR-0301, ADR-0430, ADR-0475, brief #1043, brief #1277, plan #661
- Requirements: REQ-066

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-14:

> Intake for a steward role: one session beside the owner answers every question the evidence settles, in the form AGK expects, asks the owner only real business or requirement ambiguity, keeps project memory and never leaves builders waiting.

The brief is issue #1277, under plan #661. Today the conductor answers a question "from the rules when they answer it"
and names every other decision for the maintainers; nothing else answers, and the co-owner chat that helps the owner
keeps no memory past a compaction. One evening of a customer project in local mode showed most of the owner's questions
settled by the kit's own code and state, a few that needed the owner, and three misses of the co-owner that evidence
found. The kit recognises `Answer:` and `Maintainer answer:` only by their prefixes, and the sessions and the owner post
as one login, so the login cannot show who wrote an owner's answer.

## Decision

1. REQ-066 is added to `docs/requirements.md` as `planned`, and SPEC-0059 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until the owner's own `Approve:` line approves it.
2. A steward role, `.claude/agents/steward.md` on the `strongest` tier at `high`, answers a question only when one source,
   in SPEC-0059 rule 3's order, settles it, and posts the answer with its evidence and rule. Every other question, and
   every one that changes scope, a date, a cost, the customer's sign-off or an earlier owner decision, goes to the owner
   as one plain business sentence with a recommendation.
3. The owner's reply is posted as a `Maintainer answer:` with the owner's words and time quoted verbatim, and the role's
   guard, `.claude/hooks/steward_guard.py`, refuses one without that quote, and refuses `Approve:`, `Confirmed:`,
   `Verdict:`, `Final:` and `Correction:` lines, merges, pushes to the default branch, workflow, ruleset and secret
   changes, and filing without the owner's word unless `[steward] auto_file = true` for a `Size: S` brief with no
   protected path.
4. A question for the owner never holds a builder: its pull request is parked with `agk:parked`, the builder ends and
   the slot is filled, and the owner's answer restarts a builder on the same pull request.
5. The steward's memory is one open issue labelled `agk-steward` (a sidecar file in personal mode), read first at every
   start and rolled over at 500 comments.
6. The rule on who may answer a question is principle 7 and `CLAUDE.md item 1`, not principle 1 as the brief names it;
   build (a) adds the evidence-settled class there by its own ADR. Principle 2 and session rule 2 are unchanged.
7. This is the one ADR of REQ-066 for the builds of SPEC-0059 rule 17, for what it names here. They will change these
   protected path classes: `.claude/` (the agent file and its guard), `scripts/agk/` (the steward's helpers),
   `tests/kit/`, `tests/kit_dev/` (the install test of the new files), `kit/` (the manifest entries), `agk.toml` (the
   `[[testing.map]]` entries and the `[steward]` table), `config/` (`core-rules.md`, `session-rules.md`,
   `rule-budget.txt`) and `constitution/` (principle 7, build (a) only). A build that changes a class named here and no
   other may cite this ADR with `Covered-by: ADR-0541` once it is Accepted (session rule 36), unless it changes a
   decision of an Approved spec or of an ADR or the constitution, as build (a) does, which then writes its own. No build
   changes a workflow file (`.github/`), the ruleset or `config/reviewers.yaml`; `kit/hashes.json` and the version stay
   the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that runs changes in this pull
request: until build (a) lands and a person starts `claude --agent steward`, the conductor answers as it does now.

## Residual

None beyond SPEC-0059's residual. The intake checks cannot tell whether the rules are the right ones; that is the review
of this pull request.

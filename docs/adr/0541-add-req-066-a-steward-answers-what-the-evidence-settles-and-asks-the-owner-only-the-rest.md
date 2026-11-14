# ADR-0541: Add REQ-066: A steward answers what the evidence settles and asks the owner only the rest

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: SPEC-0059, SPEC-0012, SPEC-0037, SPEC-0041, SPEC-0042, SPEC-0043, SPEC-0045, SPEC-0048, SPEC-0058, ADR-0301, ADR-0430, ADR-0475, brief #1043, brief #1277, plan #661
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
found. The owner's correction on the brief (comment 6881131563) ruled its three open questions and made the steward the
owner's one entry point, a second (comment 6881233447) set a cost and speed budget and skills first, a third (comment 6881300953) bounded
every role's wait on the owner, and a fourth (comment 6881464547) set the steward's authority by stage and its
structured notes. The kit recognises `Answer:` and `Maintainer answer:` only by their prefixes, and the sessions and the owner post
as one login, so the login cannot show who wrote an owner's answer.

## Decision

1. REQ-066 is added to `docs/requirements.md` as `planned`, and SPEC-0059 as `Draft`. Merging this pull request approves
   the requirement as a proposal; the spec stays `Draft` until the owner's own `Approve:` line approves it.
2. A steward role, `.claude/agents/steward.md` on the `strongest` tier at `high`, is the owner's one entry point: it names
   the project's stage on SPEC-0048's path, drives it with the kit's existing skills and starts the conductor when the
   plan passes its checks; the conductor starts it when a `Question:` has waited one pass. It answers a question only when one source,
   in SPEC-0059 rule 3's order, settles it, and posts the answer with its evidence and rule. Until building starts every
   requirement question goes to the owner with the steward's recommendation; from then the steward answers one the
   evidence settles, and a planning gap or a class the owner overrode twice in seven days goes to the owner. Every other question, and
   every one that changes scope, a date, a cost, the customer's sign-off or an earlier owner decision, goes to the owner
   as one plain business sentence with a recommendation.
3. The owner's reply is posted as a `Maintainer answer:` with the owner's words and time quoted verbatim, and the role's
   guard, `.claude/hooks/steward_guard.py`, refuses one without that quote, and refuses `Approve:`, `Confirmed:`,
   `Verdict:`, `Final:` and `Correction:` lines, merges, pushes to the default branch, workflow, ruleset and secret
   changes, and filing without the owner's word above the `[steward] auto_file` priority (`0` by default: only a
   `Priority: 0` brief). Kit briefs, corrections and questions go straight to the kit repository, from any project, only
   through an outbound data guard that refuses, fail closed, a text holding a project token, an e-mail address, a phone
   number, a project host or another repository's name.
4. A wait on the owner holds no role longer than `[flow] owner_wait_minutes` (30 by default), for the steward, the
   conductor and the builder alike: then the pull request is parked with `agk:parked`, the builder hands over and takes
   its next brief, the slot is filled, and the owner's answer, whenever it comes, resumes a builder on the same pull
   request ahead of new briefs of its milestone. Session rule 21's wait changes by build (c)'s own ADR.
5. The steward spends little: it reads through the kit's cached and conditional readers, runs `session.py plan` at most
   once per start, routes mechanical answers below `strongest`, and holds a measured budget of at most 15 counted GitHub
   calls for a pass that answers one mechanical question and 5 for a quiet start. It uses the kit's skill for every stage
   and step it covers, and files a kit brief for a missing one.
6. The steward's memory is one open issue labelled `agk-steward` (a sidecar file in personal mode), read first at every
   start and rolled over at 500 comments.
7. The rule on who may answer a question is principle 7 and `CLAUDE.md item 1`, not principle 1 as the brief names it;
   build (a) adds the evidence-settled class there by its own ADR. Principle 2 and session rule 2 are unchanged.
8. This is the one ADR of REQ-066 for the builds of SPEC-0059 rule 17, (a) to (e), for what it names here. They will change these
   protected path classes: `.claude/` (the agent file, its guard and the conductor's guard for the steward's start), `scripts/agk/` (the steward's helpers),
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

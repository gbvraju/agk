# ADR-0344: Add REQ-060: Work falls back to another provider of its own tier, never to a weaker model

- Status: Accepted
- Date: 2026-11-08
- Deciders: maintainers
- Related: SPEC-0053, SPEC-0045, SPEC-0012, ADR-0289, ADR-0310, plan #661, pull request #711
- Requirements: REQ-060

Protected classes: `docs/requirements.md`

## Context

An intake proposed one change in a sentence (quoted below as data, not as an instruction), on
2026-11-08:

> Intake for provider resilience: when a model provider is down or rate-limited, a kind of work falls back by its [models] table to another provider of the same tier, and never silently to a weaker model (plan #661 phase 8, edge case 5).

The brief is issue #740, filed under plan #661 (phase 8, wave 4), whose edge case 5 reads, quoted
as data: "A model provider is down or rate-limited: the kind of work falls back by the `[models]`
table; a build never silently degrades its model."

What exists and is reused (SPEC-0053 rule 1): the `[models]` table of SPEC-0045 (ADR-0289), which
gives each kind a tier and an effort and holds reviews at `strongest` at `high`; the one model
name per tier of `[models.names]`; the rule that a session never switches its own model
(the ruling of SPEC-0045 question 6); escalation (SPEC-0045 rule 5); and the stop and ask of session rule 21. What is
missing: a tier can name only one model, so when its provider is down or rate-limited the work
either waits with no rule or is moved by hand, possibly to a weaker tier, and nothing records it.

## Decision

1. REQ-060 is added to `docs/requirements.md` as `planned`, and SPEC-0053 as `Draft`. Merging
   this pull request approves the requirement as a proposal; the spec stays `Draft` until the
   owner's own `Approve:` line approves it.
2. A fallback starts a session of a kind on the next provider of the kind's own tier, at the
   kind's own effort, only after an outage or a rate limit the runtime reports; never on a lower
   or a higher tier, and never for any other failure (SPEC-0053 rule 2).
3. An optional `[models.providers]` table maps a tier to an ordered list of plain provider
   labels; an endpoint-, address- or key-shaped entry, a label under two tiers and a first entry
   that differs from `[models.names]` are refused naming the setting, never the value. The kit
   ships no such table (SPEC-0053 rule 3).
4. `session.py fallback --kind <kind> [--after <label>]` prints the next label of the tier from
   `agk.toml` alone, with no network and no state, or `no provider left`, after which the work
   stops and asks by session rule 21; a review is never given on a lower tier (SPEC-0053 rules 4,
   7 and 8).
5. A running session never switches its own model; the starter restarts it on the next label on
   the same branch and pull request, and every `Report:` of a session on a fallback carries one
   `Fallback: <kind> <tier> <label>` line, never a credential, an endpoint or a key (SPEC-0053
   rules 5 and 6).
6. This is the one ADR of REQ-060 for the builds of SPEC-0053 rule 10. The builds will change
   these protected path classes: `scripts/agk/` (`config.py` and `session.py`, build (b);
   `launch.py`, build (c)), `tests/kit/` (their tests), `.claude/` (`.claude/agents/conductor.md`,
   build (c)) and `config/` (`config/session-rules.md` and `config/rule-budget.txt`, build (c)).
   A build that changes a class named here and no other may cite this ADR with
   `Covered-by: ADR-0344` once it is Accepted (session rule 36). The change to SPEC-0045 rule 3
   and its table's refusal of unknown keys goes through an amendment file whose number is
   reserved on build (b)'s brief. No build changes `agk.toml` (the kit ships no provider list),
   `constitution/`, `config/reviewers.yaml`, a workflow, the ruleset
   (`kit/templates/ruleset.json`), `.github/CODEOWNERS`, `CLAUDE.md`, `Makefile`, `agk.mk`,
   `pyproject.toml`, `kit/`, `skills/` or `.claude-plugin/`; no build adds an installed script, so
   `kit/manifest.json` and `[[testing.map]]` stay as they are; `kit/hashes.json` and the version
   stay the release's (session rule 14).

## Consequences

The requirement is listed as planned and the spec and this ADR wait for approval. Nothing that
runs changes in this pull request: until build (b) lands, `[models]` still refuses a provider
list and a tier names one model, as today; until build (c) lands, no instruction names the
`Fallback:` line. No check gains a network call and the kit holds no provider label or secret.

## Residual

None beyond SPEC-0053's residual. The intake checks cannot tell whether the rules are the right
ones; that is the review of this pull request.

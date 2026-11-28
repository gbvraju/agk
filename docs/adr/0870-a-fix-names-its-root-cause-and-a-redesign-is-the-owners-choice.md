# ADR-0870: A fix brief names its root cause and fix type; a redesign is the owner's choice by stage

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers
- Related: ADR-0752, ADR-0756, ADR-0757, ADR-0774, ADR-0594, ADR-0850, ADR-0303, ADR-0301, ADR-0558, ADR-0560,
  ADR-0852, SPEC-0032, SPEC-0046, SPEC-0059, REQ-037, REQ-066, brief #2095
- Requirements: REQ-037, REQ-066

Protected classes: `scripts/agk/`, `tests/kit/`, `.claude/`, `kit/`, `agk.toml`, `config/`

## Context

Of the newest 100 kit briefs none names a root cause, while 89 say `Class: ...; seen 1` or more: the same cause is
patched again and nothing links the patches (brief #2095). The owner agreed the rule in the steward chat on
2026-11-28: a fix names its root cause and fix type, a redesign is the owner's choice by stage and release, and a
recurrence is counted on one parked root-cause brief, never filed twice.

## Decision

1. A fix brief (one with a `Fix type:`, `Root cause:` or `Root-cause:` line, or a `Priority: 0` that is not the
   router's pair `Advances: none` with `Priority: 0`) carries exactly one `Fix type: root|patch|redesign` and exactly
   one `Root cause: <cause>: <why>; before: <refs or none: <search>>; removed by: <design>`, the cause a key of
   lower-case words joined by `-`, at most 60 characters. `patch` carries exactly one `Root-cause: #n`; `root` and
   `redesign` carry none; `redesign` carries a `Priority:` line. An `ADR-` id in `before:` must exist.
   `brief_study.root_cause_problems` holds these as the other study lines: warned before `[flow]
   brief_study_fails_from`, failed from it, each naming the line (`setting: Root cause:`), never its text.
2. From the open briefs (the plan's read cache or `--open-briefs FILE`, leaving out the brief's own number), a
   `root` or `redesign` brief whose cause is an open `Fix type: redesign` brief's fails naming that `#n` and the
   lines to write; a `patch` whose `Root-cause: #n` is not an open redesign brief of the same cause fails naming the
   line. Causes match exactly. With no cache: one warning, `study: root causes not read (no plan cache)`.
   `brief_study.py` prints the open causes as `cause <key> #n`.
3. `steward_evidence.py root-cause --brief FILE [--redesign FILE] [--date DAY] [--triage T]` prints the decision
   packet of a redesign (exit 3): cause, open root-cause brief, stage, release (the earliest open milestone dated on
   or after the day, among `[plan] active_milestones` when set; in personal mode the `Target:` lines of
   `docs/plan/milestones.md`, with no GET), recommendation and why, cost from the drafts' `Expected:` lines,
   reversibility and impact (kit and projects in the kit; this project in a project). `root` prints `no packet`, an
   open root-cause brief of the cause prints `recurrence: #n` and a kit triage in a project prints `kit defect:`,
   each exit 0.
4. Before `build`, or in `build` with no dated release: `redesign now`; in `build` with a dated release: `patch now;
   root-cause brief parked until after <milestone>`; milestones unread: `the owner decides`.
5. `steward_owner.file_brief`, filing a `patch`, counts the `Recurred:` comments on its root-cause brief and posts one
   `Recurred: <k+1> times; newest #<new> (<day>)` with `Who: AGK steward`; in personal mode it prints the line.
   `steward_daily.daily_text` adds per day `Root cause recurred (<day>): #n <k> times, newest #m`, `none` or
   `unknown`. No other script writes `Recurred:`.
6. `steward_evidence.triage` refuses a brief finding with `cause` whose text has no `Fix type:` or `Root cause:`
   line, naming rule 7 and the line.

## Consequences

A cause has one root-cause brief and each patch is counted on it and raised on the owner's daily list. The study
grows by one rule set read from the brief and the cache; the packet adds at most two GETs per redesign. No workflow,
label, ruleset, required check or `governance_map.CHECKS` change. The `[[testing.map]]` entries of the four scripts
in `agk.toml` gain `tests/kit/test_root_cause.py`; `.claude/agents/steward.md` gains one sentence and loses the relay form that
`steward_owner.py relay` already checks, so `config/rule-budget.txt` lowers its line; `kit/hashes.json`, a release file, is left to the release.

## Residual

- 2026-11-28: `Q-2095-1`: the packet's `impact:` effects are fixed words (the kit's own rules and every project at
  its next kit update; or this project only), not read from the drafts, since the brief names no source for them.

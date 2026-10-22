# ADR-0075: discovery before design and the slicing rule (REQ-030 part b, SPEC-0023), kit 0.41.0

- Status: Proposed
- Date: 2026-10-22
- Deciders: maintainers
- Related: ADR-0073, ADR-0074, ADR-0043
- Requirements: REQ-030

Protected classes: `scripts/agk/`, `skills/`, `tests/kit_dev/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

SPEC-0023 (Approved, #124) asks the product owner what the problem statement leaves open before the charter is written, and records what is not known with the slice that breaks if it is wrong. Its build is split
in three; this part (b) builds `/agk:start` discovery and the slicing rule with `check-start` (rules 6 and 7; AC5 and AC6). The tests were written first and run on unchanged `main` (21 failed, 5 passed; the output
is in the pull request body).

## Decision

1. **Discovery in the skill**: `skills/start/SKILL.md` gains a step before the charter that asks about six topics named `users`, `existing`, `runs`, `data`, `scale` and `compliance`, only those the statement
   leaves open, at most three questions per round, `not known yet` being an allowed answer. The files written are still exactly two.
2. **The charter**: its Decision gains the numbered item **Discovery** (one bullet per topic, in order) and **Slice** (one bullet per topic answered `not known yet`, and for any other topic the first slice leaves
   out; the item may be absent when there is none).
3. **The check**: `playbook.py check-start` refuses a charter without the Discovery item, a topic, an answer, the order, or the Slice bullet of a topic answered `not known yet`, and a Slice bullet that names no
   topic or says nothing. Messages name the rule and the topic, never the answer. It runs on a start only; a charter from before this change is not checked again and no governance check reads the item.
4. **Amendment 38** (`docs/runs/proposed-spec-amendments-38.md`) is applied to SPEC-0013 rules 4 and 5.
5. **Tests, first** (`tests/kit_dev/test_start_discovery.py`, new, kit-only): the six topics present, missing, unanswered and out of order; `not known yet` with and without its Slice line; a Slice bullet for a known
   topic; an old charter in the base; no other script reads the item; the skill's questions, limit and two-file rule. `tests/kit_dev/test_playbook.py` gains the Discovery item in its good charter.
6. **Kit 0.41.0**: the manifest `kit_version`, the hashes, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7).

## Consequences

- A project started after the upgrade has a charter that says what was asked and what is not known yet. A project started before it is not disturbed.
- Part (c) (the shadow record and the counting script) follows with kit 0.42.0.

## Residual

None. The residual line the maintainers queued for this pull request (a kit upgrade's proof) is in `docs/runs/residuals.md`, owner maintainers, due 2026-12-31.

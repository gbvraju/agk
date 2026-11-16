# ADR-0558: The steward answers from evidence and triages findings

- Status: Accepted
- Date: 2026-11-15
- Deciders: maintainers
- Related: SPEC-0059, ADR-0557, SPEC-0048, brief #1321, brief #1320, plan #661
- Requirements: REQ-066

## Context

SPEC-0059 (Approved, #1280) rule 17 orders six builds of the steward; build (a) (brief #1320, ADR-0557) added the
agent file, its guard, the `[steward]` setting and the memory. On the default branch nothing reads the sources of rule 3
in order, writes the answer form `Answer: Q-<id> <answer> (evidence: …; rule: …)`, reads the project's stage or
triages a finding (brief #1321's evidence). This ADR covers build (b): rules 2 (the stage), 3, 4, 6, 7, 9, 12 and 19.

## Decision

1. **The rule, not the reading.** `scripts/agk/steward_evidence.py` applies rule 3 to what the steward read and wrote
   into a question file (each finding's source, 1 to 5 in rule 3's order, its answer, place and rule); it reads no
   source itself and calls no model. The first source that answers wins. The question goes to the owner when no
   finding answers it; when findings disagree and no `ranking` (an earlier decision) names the source that wins; when
   its class is business, scope, date, cost or sign-off, or it changes one of them; or when it reverses an owner
   decision.
2. **The stage.** `stage` reads SPEC-0048's guided path in the owner's words (`Q-S0059-10`), newest first: `build`
   while an `agk-conductor` issue is open (one GET; never in personal mode, where it reads as planning); `plan` with
   `docs/plan/milestones.md` or `docs/plan/scope-lock.md`; `stack and technical design` with a
   `docs/adr/*-stack-options.md`; `prototype and design` with a discovery document in front door phase 4 or 5; `scope`
   with `docs/plan/scope.md`; `vision and discovery` with any discovery document; otherwise `start`. An open conductor
   issue stands for the steward's start of the conductor until build (c) adds that start (`Q-1321-1`).
3. **Authority by stage.** In planning every requirement question goes to the owner with the recommendation and
   evidence that `settle` prints; the steward answers technical questions. In building a requirement question that
   no finding of sources 1 to 4 names is a planning gap: it goes to the owner and `settle` prints the `Gap:` note to
   record. An answer settled by source 2, 3 or 4 is a requirement answer; until build (d)'s re-check lands it goes to
   the owner with its recommendation and is never posted.
4. **The answer.** `answer` posts one comment on the issue or pull request named, first line the form of rule 4 and
   last line `Who: AGK steward`, and posts nothing for an owner question. One mechanical pass (start, stage, one read,
   one answer, end) stays within rule 18's 15 counted calls, measured with the recorded `gh` double.
5. **Triage.** `triage` judges one finding: exactly one of `kit brief`, `kit correction`, `kit question`, `project
   brief` or `owner question`, with its `Triage:` note. A filing is refused, naming the setting or list and never the
   value, without its `Modes: github …; local …; personal …` line, with a cause not reproduced on the default branch,
   when a brief fails `check_brief.py`'s `body_problems` (against the project's root for a project brief), when the
   text holds a token of `config/neutrality.txt` (the list `check_neutrality.py` reads, applied to the text; a list
   that cannot be read refuses), or above `[steward] auto_file` (a correction or question has no priority, so it
   always needs it) without an `Owner said (<UTC time>): "…"` line, the form the guard accepts. A kit filing from a
   project (a root without `kit/manifest.json`) prints `draft:` for the owner until build (e)'s outbound data guard.
6. **Skills first.** `skill` reads rule 19's table from the agent file, the one copy, and prints the step's skill or
   `no skill:` with one kit brief to triage.
7. **The agent file** names each command, and its words go from 549 to 645 in `config/rule-budget.txt` (ADR-0310);
   no rule line is added. The detail of the file forms is in `docs/guides/reference.md`.

## Consequences

The steward's judgement stays the model's, but each answer, owner question and filing passes one tested rule.
Protected path classes changed: `.claude/` (`agents/steward.md`), `scripts/agk/` (`steward_evidence.py`), `config/`
(`rule-budget.txt`), `agk.toml` (the `[[testing.map]]` entries), `tests/kit/` (two new test files) and `kit/`
(`manifest.json`).

## Residual

- 2026-11-15: the owner relay and the conductor's start (c), the re-check and daily list (d), the outbound data guard
  (e) and onboarding (f) are later builds.

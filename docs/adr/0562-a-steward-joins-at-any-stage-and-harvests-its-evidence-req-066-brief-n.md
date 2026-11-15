# ADR-0562: A steward joins at any stage and harvests its evidence

- Status: Proposed
- Date: 2026-11-15
- Deciders: maintainers
- Related: SPEC-0059, ADR-0557, ADR-0558, brief #1325, brief #1320, brief #1321, plan #661
- Requirements: REQ-066

## Context

SPEC-0059 (Approved, #1280) rule 17 orders six builds of the steward; build (a) (brief #1320, ADR-0557) added the
memory and build (b) (brief #1321, ADR-0558) the stage reading and the evidence rule. On the default branch no command
reads a repository's existing `Maintainer answer:` lines, Accepted ADRs and decision files into the steward's memory, so
a steward joining a running project would ask the owner what the repository already records (brief #1325's evidence).
This ADR covers build (f): rule 20, with rule 18's budget as `Q-S0059-15` reads it.

## Decision

1. **One command, two names.** `scripts/agk/steward_onboard.py onboard [--again]` holds the onboarding;
   `steward.py onboard [--again]` runs it, the subcommand `Q-S0059-14` names.
2. **Three entry points**, read only at a first start (a memory with no `Onboarded:` entry; a later start writes
   nothing). Execution: an open `agk-conductor` issue (the stage `build`), or `docs/plan/scope-lock.md` and a closed
   `agk-brief` issue (work merged). Day 0: the stage `start`, no Approved spec under `docs/specs/` and no `agk-brief`
   issue; nothing is harvested. Otherwise planning, under the stage `steward_evidence.py stage` names.
3. **The harvest** (planning and execution) reads by list pages only, never one read per item: the repository's
   issue and pull request comments (`issues/comments`, a hundred a page), the open `agk:parked` issues, and the files.
   It reads each comment's first line: a `Maintainer answer:` or `Answer:` is a decision of its Q id; two that disagree
   on one Q id are an owner question naming both sources, never a decision; a `Question:` with no answer and an
   `Owner needed:` with no later `Maintainer answer:` on its issue are open questions. From the files: Accepted ADRs,
   the rows of `docs/runs/decisions/`, Approved specs, the statuses of `docs/requirements.md`, the `design` rows of
   `docs/design/signoffs.md` and the last line of `check_plan.py --trace` where `docs/plan/` exists.
4. **The notes.** Each line cites its source and each note says `harvested`. Decisions, gaps and risks are grouped
   in notes of at most 50 lines under one first word (`Decision:`, `Gap:`, `Risk:` for parked work), so a repository
   of hundreds of ADRs costs a few posts, not hundreds; each owner question is its own `Owner question:` note, so the
   memory's roll-over carries its Q id. A source that cannot be read is a `Gap:`, never assumed empty. A line the data
   guard (SPEC-0042) matches is withheld, naming the class, never the value. The last note is `Onboarded: <stage>
   <date>, <n> decisions, <n> gaps, <n> open questions`, and the command prints the summary for the owner: the entry,
   the stage, the decisions it relies on and the gaps.
5. **Authority after onboarding** is the agent file's: at a first start the steward runs `onboard` before any answer,
   and in execution answers only from its notes and newer facts.
6. **Re-onboarding.** `--again` harvests again and writes only the lines no note holds, then a new `Onboarded:` entry.
7. **Personal mode** reads the files only and writes the sidecar memory file; nothing is posted.

## Consequences

A steward joining a running project has the project's decisions in its memory before it answers, at a bounded cost:
in the recorded double, 150 comments are read in 2 pages and the first onboarding makes 6 reads and 6 posts. Protected
path classes changed: `.claude/` (`agents/steward.md`, its words held at 645), `scripts/agk/` (`steward_onboard.py`,
`steward.py`), `agk.toml` (the `[[testing.map]]` entries), `tests/kit/` (one new test file) and `kit/`
(`manifest.json`).

## Residual

- 2026-11-15: a contradiction is read as two different answer texts for one Q id; two answers worded differently that
  mean the same go to the owner too, the conservative reading (due 2027-03-31).

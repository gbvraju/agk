# ADR-0508: Open questions become issues for business

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: ADR-0459, ADR-0461, ADR-0506, ADR-0507, SPEC-0043 rules 6, 7 and 25, brief #1196, plan #661
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

`plan_intake.py render` prints `Conflicts for the person` and `Open questions for the person`, each with its source
location, and writes them nowhere GitHub shows; `publish` prints one `gh api` command per milestone and per brief only.
The owner asked (2026-11-13) for a board business can read: three views (Sign-off, Questions, Roadmap) and open
questions as issues, so that business answers in the issue and an answered question closes. Builders take only issues
labelled `agk-brief`, so an issue with another label is never picked up as work.

## Decision

1. `render` writes, after the five scope headings of `docs/plan/scope.md`, one section `## Questions for business`:
   a `### <key>` block per open question (its key) and per conflict the person has not settled (`conflict-<n>`, its
   place among the conflicts; a settled conflict has its answer), each with `Question: <text>`, `Source: <locations>`
   and `Blocks: <keys>`, or `- none`. `Blocks:` names the requirements that cite one of the question's locations and
   the briefs that cite one or advance such a requirement, by key, or `none`; the person may edit it.
2. `publish` reads that section, never the proposals file outside `docs/`. After the milestones and before every brief
   it prints `gh label create agk-business-question ... --force` once, then one `gh api` command per question not yet
   in `--numbers`: an issue titled with the question's plain text (its `(verify)` mark left out, at most 256
   characters), its body `## Question`, the text, `Source:`, `Blocks:` and an empty `## Answer`, labelled
   `agk-business-question` and never `agk-brief`. A question already in `--numbers` is printed `published <key> #<n>`
   and never again. A question key that repeats, or repeats a brief key or a milestone id, is refused (one number per
   key). In personal mode the questions are written first through the files forge, as briefs are.
3. A brief that a question's `Blocks:` names waits for the question's number (`withheld <key>: waits for ...`), and
   its issue then carries one `Blocked-by: #<n>` line per question, in the visible part before the hidden brief.
4. `session_plan.running_conflict`, which `session.py plan`, `next` and `claim` share, first reads each `Blocked-by:
   #<n>` issue once per survey with one GET: while it is not closed the brief waits, printed `waits for question #<n>`
   (with `(it cannot be read)` when the read fails, which is never taken as closed), and is not offered to builders.
5. `board.py` reads the open `agk-business-question` issues beside the briefs (one REST read a label) and adds them to
   the board with a single-select field `Type` (Work, Question) set to Question and `Sign-off` left empty. `Type` is
   added once a question is there; on the run that adds it, the cards already on the board get Work once, so a value a
   person set is never overwritten (ADR-0507 decision 2).
6. `docs/guides/planning.md` steps 7 and 9 say it in two sentences.

## Consequences

Each open question and unsettled conflict is an issue business answers, on the board's Questions view, and the briefs it
blocks wait until it closes. A question published by hand, without `Blocked-by:` on the briefs, holds nothing.

## Residual

- 2026-11-13: `gh label create --force` is read from the `gh` manual, not run here: a cloud session runs no `gh label`
  (verify on the owner's machine; due 2027-01-31).
- 2026-11-13: a `Blocks:` key that names only a requirement holds no brief once the briefs carry `REQ-n` numbers;
  `render` lists the briefs that advance it beside it, so the person keeps both when editing (due 2027-01-31).

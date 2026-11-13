# ADR-0507: The board is copied from a template and carries business fields

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: ADR-0506, SPEC-0043 rule 25, ADR-0481, brief #1195, brief #1190, plan #661
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `skills/`

## Context

`/agk:board` (ADR-0506) creates an empty Project, adds `Size` and `Expected hours` and adds every brief issue. It makes
no views, and GitHub's API cannot make one: views are made in GitHub's own screen, so on every project the owner would
build them by hand. The owner asked (2026-11-13) for a board that business can read and sign off from: three views
(Sign-off, Questions, Roadmap) copied from one template board, the fields Persona, Requirement, Screens and Sign-off,
and open questions as issues. `gh project copy` copies a Project with its views, fields and columns. A published brief
issue (ADR-0481) shows `## What` and `## Acceptance` and carries `Advances:` and `Screens:` lines, but no persona.

## Decision

1. `board.py` takes `--template <owner>/<number>`, else `[plan] board_template = "<owner>/<number>"` of `agk.toml`
   (read by `common.plan_settings`; anything else is a refusal that names the setting). On the first `--yes` run (no
   board named) it copies that Project with `gh project copy`, titled `<repository> plan`, under the repository's
   owner, instead of creating an empty one, then links the repository and prints the `board = <n>` line as before.
   Without a template it creates the board as ADR-0506 does and prints one line naming the three views to make once:
   Sign-off (a board by Status), Questions (a table), Roadmap (by Milestone). A board already named is never copied.
2. Each run adds, when the board lacks them, the fields `Persona`, `Requirement` and `Screens` (text) and `Sign-off`
   (single select Pending, Signed off, Changes asked) beside ADR-0506's two. On each card it adds, it fills Persona,
   Requirement and Screens from the issue's own `Persona:`, `Advances:` and `Screens:` lines and sets Sign-off to
   Pending. ADR-0506's rule that an item already on the board is never edited stands, with one exception: a business
   field that this run added to the board is filled once on the cards already there, which have no value in it. So a
   value a person set is never overwritten.
3. `plan_intake.py publish` writes one `Persona: <key> <name>` line in the visible part of each brief issue, before its
   milestone line: the persona of the requirements its `Advances:` names, from their block of
   `docs/plan/requirements-proposed.md`, else from their section of `docs/requirements.md`. Distinct personas are
   joined by `, `, and there is no line when no requirement names one. The hidden brief stays unchanged, and the issue
   still passes `check_brief.py --root`.
4. `docs/guides/planning.md` step 9 says how to make the template board once and how business signs off. The board's
   Sign-off is a reading aid. The plan's formal gate stays the owner's `Approve: plan <full head ID>` line.

## Consequences

The owner makes one template board, and every project's board then has the three views and the business fields with no
work by hand. A business reader reads a card in plain words (what, acceptance, persona, screens) and sets its Sign-off.
The board is still not a record: the plan's approval and the brief's decisions stay on GitHub's issues and pull
requests.

## Residual

- 2026-11-13: `gh project copy <number> --source-owner --target-owner --title --format json` is read from the `gh`
  manual, not run here: a cloud session cannot reach Projects (verify on the owner's machine; due 2027-01-31).
- 2026-11-13: a card whose issue gains a `Persona:` or `Screens:` line after it was added is not refilled. A later
  build may fill empty values on every run once `item-list`'s values are read (due 2027-01-31).

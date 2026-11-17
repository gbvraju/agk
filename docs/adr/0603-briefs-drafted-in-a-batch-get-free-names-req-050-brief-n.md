# ADR-0603: Briefs drafted in a batch get free names

- Status: Proposed
- Date: 2026-11-17
- Deciders: maintainers
- Related: brief #1442, ADR-0598, Q-1425-2
- Requirements: REQ-050

Protected classes: `skills/`, `tests/kit/`, `tests/kit_dev/`

## Context

ADR-0598 gave `plan_names.py batch` free names for a whole batch of new folders, but the `brief` skill, through which
the steward and a person draft briefs, named no such step: a batch drafted by hand could still reuse an earlier batch's
folder names, and the clash showed only at `check_brief.py` or the next plan run. The steward's own file is at its word
budget, so the step cannot live there (Q-1425-2).

## Decision

1. The `brief` skill (`skills/brief/SKILL.md`) says: before an `Adds:` line names a new folder or file, write one base
   per line, by the convention `<feature>-m<milestone>-<part>`, run `plan_names.py batch FILE` and use the names it
   prints; one new brief alone uses `next --base`. Then check each saved brief with `check_brief.py BRIEF --root .`
   before it is filed.
2. `plan_intake.py` is unchanged: `brief_text` writes no `Adds:` line. A test holds that, so a later change that adds
   one fails it and must take each new name from `plan_names.batch` for the whole intake in one pass.
3. `tests/kit_dev/test_distribution.py` lists `plan_names` and `check_brief` among the scripts the `brief` skill runs.
4. `docs/guides/planning.md` "New paths have one owner" names the skill's step.

## Consequences

A batch drafted through the skill is named in one pass, free of the tree, every open brief (parked and taken ones
included) and every open pull request. The skill's command lines are tested against the ones the reference lists.

## Residual

- The skill is prose: a session that skips the step is still caught by `check_brief.py --root` at filing, or by the
  plan's `CLASH:` line.

# ADR-0679: In solo mode the steward does the setup and records each choice

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1599, SPEC-0062, SPEC-0048, SPEC-0001, ADR-0678, ADR-0557, plan #661, amendments 208 and 209
- Requirements: REQ-069

## Context

SPEC-0062 (Approved) rule 18 build (b) builds rules 8, 9 and 11: in solo mode the steward settles every AGK matter
from the kit's defaults, records each, does the setup through the kit's commands, and the person edits no file but the
`[delivery] work_type` line. On the default branch `steward.py record --kind Setup` is refused as not a memory kind,
`kit/templates/reviewers.yaml` holds `@REPLACE-ME` twice and getting-started step 4 has the person edit both, nothing
writes `review_mode = "solo"` in a new project (SPEC-0062 rule 2 and `Q-S0062-7` say the steward never changes it),
and `project_tests` is empty after `adopt`.

## Decision

1. `steward.py` gains the memory kind `Setup`, recorded as `Setup: <setting or matter>: <choice> because <reason>`
   and ending `Who: AGK steward`; any other form is refused, naming the rule, never the text.
2. `steward.py setup [--adopted] [--detect FILE] [--answer TEXT]` prints one `Setup:` line for each AGK matter, from
   the kit's defaults: the models (one route, no `[models.routes]`), the builders (one per brief), `max_builders`
   (`session.MAX_BUILDERS`), `pr_mode` (strict) and the reviewers file (the signed-in login); adopted, also
   `project_tests` proposed from the stacks of `front_door.py detect --json` (a fixed command per stack row, in its
   folder). It asks only two plain questions: "Will you run this alone, or with a team? Alone (recommended for one
   person) · with a team" and "When do you rest?" (`owner_rest_hours`). With the person's `--answer` it adds the
   `Setup: review_mode:` line with their words and prints the `run:` install command. In a project already installed
   (`agk.toml` `mode`) `--answer` is refused naming `review_mode`: the steward never changes it after setup.
3. `init.py` and `adopt.py` gain three setup flags, applied to the install's own files before CODEOWNERS is rendered:
   `--login-from-env` writes the login in `AGK_SETUP_LOGIN` on both `@REPLACE-ME` lines and drops the install ADR's
   placeholder residual; `--solo` writes `review_mode = "solo"` and one decision line in ADR-0001 of the install, and
   is refused naming `review_mode` while the reviewers file holds the placeholder; `--project-tests CMD` writes
   `project_tests`. Init and adopt still run no command and reach no network (SPEC-0001, REQ-009 rule 3): the steward's
   `run:` line reads the login with `gh api user --jq .login` into the variable, so it is never printed.
4. Two proposed amendments, for the owner's approval: 208 (SPEC-0062 rule 2: the setup answer may set `review_mode`
   only at setup, through the install pull request with its ADR) and 209 (SPEC-0048 rule 5: an unclear kind is written
   as `unclear (proposed)` and planned as an enterprise product, and `pilot (proposed)` only on the person's words). The code of decision 2 and 3 follows 208's
   reading; the discovery document's text is unchanged until 209 is approved.
5. The guide's `## Solo mode` gains a Setup bullet (rules 8, 9 and 11, and the one test run of a proposed command);
   the role file's `Solo.` paragraph names `steward.py setup`, and its words stay at the budget of 943 (ADR-0310).

Protected path classes changed: `.claude/` (`agents/steward.md`), `scripts/agk/` (`steward.py`, `init.py`,
`adopt.py`), `tests/kit/` (`test_steward_setup.py`) and `agk.toml` (the `[testing]` map entries of `steward.py`,
`init.py` and `adopt.py`).

## Consequences

A solo person who lets the steward run the install edits no reviewers line and no setting, and every AGK choice can be
read back as a `Setup:` entry. `review_mode` is still written only by a pull request with its ADR, now the install's
own. Without the setup flags init and adopt behave exactly as before. The steward running `setup` is the role file's
instruction, not a guard.

## Residual

- 2026-11-20: the code reads `review_mode` from the person's answer before amendment 208 is approved; if the owner
  rejects it, `--solo` and `--answer` are removed by a later brief (due 2027-03-31).
- 2026-11-20: the per-stack test commands are fixed in `steward.py`, not in `config/stack-signals.toml`; a stack
  added there gets no proposal until it is added here (due 2027-03-31).

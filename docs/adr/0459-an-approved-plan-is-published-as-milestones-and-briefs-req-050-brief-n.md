# ADR-0459: An approved plan is published as milestones and briefs

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0041, SPEC-0037, SPEC-0030, ADR-0269, ADR-0461, amendment 163, brief #1078, plan #661
- Requirements: REQ-050

## Context

SPEC-0043 (Approved, REQ-050, ADR-0269) rule 8 says nothing is created until the person confirms the plan with
`Approve: plan <full head ID>`, and rule 25 says `plan_intake.py publish` then prints one `gh api` command per
milestone and per brief, in `depends_on` order, runs none, refuses a brief that `check_brief.py --root .` fails, and
in personal mode writes the same through the file forge. Build (c2) (ADR-0461) renders the briefs with requirement
keys on `Advances:` and brief keys on `Depends-on:`. GitHub's issue API takes a milestone's number, not its title, and
`forge.FilesForge` (SPEC-0041) keeps issues, pulls and comments but no milestones.

## Decision

1. `python3 scripts/agk/plan_intake.py publish --comments FILE --head SHA [--numbers FILE] [--root DIR]` keeps the
   guard gate of rule 3. `--head` is a full head ID (40 hex), `--comments` a saved JSON list of the plan pull
   request's comments, `--numbers` a JSON object from a milestone id or brief key to its number; anything else is
   the usage line or a refusal naming the option, exit 2.
2. Rule 8: `reviewers.py` gains `APPROVE_PLAN` beside `APPROVE_DESIGN` and `plan_approvals`, read like
   `design_approvals`: the first line `Approve: plan <full head ID>` by an account of `spec_approvers`, never one
   posted through an app of `agent_apps`; `confirmed_comments` adds such a line naming the confirmed head, so in solo
   mode it counts inside the person's whole `Confirmed:` comment (session rule 29). Without one naming `--head`,
   `publish` exits 2 naming the missing confirmation and the setting, never the head.
3. It reads `docs/plan/milestones.md` (`### M<n> <title>`, `Target:`) and `docs/plan/briefs/M<n>/<key>.md`, and
   refuses with exit 1, naming the rule and the key, a brief with no `# <title>` line, a folder that is not a
   milestone, a `Milestone:` line that is not its folder, a `Depends-on:` that names no brief, a cycle, and any brief
   not yet published whose body, with its keys numbered, `check_brief.body_problems` fails with `--root`. A refusal
   prints no command at all.
4. In GitHub mode it prints, and never runs: one `gh api repos/{owner}/{repo}/milestones -X POST` per milestone not
   in `--numbers` (`title` `M<n> <title>`, `due_on` `<Target>T00:00:00Z` when `Target:` is a date), then the briefs
   in `depends_on` order (free briefs by milestone, then key): `published <key> #<n>` for one in `--numbers`,
   `withheld <key>: waits for <names>` for one whose milestone or dependence has no number yet, otherwise one
   `gh api repos/{owner}/{repo}/issues -X POST` with the title, the body with every `Depends-on: <key>` as
   `Depends-on: #<n>`, the label `agk-brief` and `-F milestone=<n>`. The values are shell-quoted. It ends with one
   `ok publish:` line of counts and `nothing was run`.
5. In personal mode (a `[personal]` table at the root, SPEC-0041) the root is the sidecar: it writes each brief not in
   `--numbers` with `FilesForge.create_issue` (label `agk-brief`), in the same order, numbering each `Depends-on:`
   from the issues just written, and prints `created <key> #<n>`. The files forge has no milestones: each milestone
   prints one line, and a brief keeps it in its `Milestone:` line.

Protected path classes changed: `scripts/agk/` (`plan_intake.py`, `reviewers.py`) and `tests/kit/`
(`test_plan_publish.py`). `kit_hashes.py` is run; no file of `kit/` is edited by hand.

## Consequences

A person who approves a plan gets the exact commands that create its milestones and briefs, in an order where every
`Depends-on:` names a real issue, and nothing reaches GitHub until they run them. A plan whose briefs are not ready
(a requirement key not yet numbered) prints nothing to run.

## Residual

- 2026-11-12: `publish` does not compare the plan files with the approved head; the person runs it on the tree they
  approved (`Q-1078-2`) (due 2026-12-31).
- 2026-11-12: personal mode records no milestone object, only each brief's `Milestone:` line (`Q-1078-1`) (due
  2026-12-31).

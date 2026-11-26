# ADR-0836: The path from an idea takes four stage pull requests

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers (the owner's yes on brief #2021, 2026-11-26T19:31Z)
- Related: ADR-0515, ADR-0564, ADR-0664, ADR-0671, SPEC-0029, SPEC-0037, SPEC-0043, SPEC-0062, REQ-050, brief #2021, plan #661
- Requirements: REQ-050

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`

## Context

`docs/guides/planning.md` asked one merged pull request per step of the path from an idea, about ten before the first
build; the v1 acceptance run (#1772) counted 6 merges and 4 pastes before it. No ADR decision states that rule: ADR-0515
decision 3 adds the guide section and ADR-0664 item 4 says the day-zero file goes in the person's pull request, approved
as any. The skills `stack`, `start` and `vision` repeated it. The code does not need the separate merges:
`engines.py stack-accept` needs a branch that is not the default branch, `check_adrs.py` holds only an ADR that is
Accepted on the merge base, and each approval (`Approve: inventory`, `Approve: design`, `Approve: plan`) names its head,
with the inventory and design rows of `docs/design/signoffs.md` tied to their record's digest.

## Decision

1. **Four stage pull requests.** With `[plan] stage_pulls = "stage"`, the stages of `steward_evidence.STAGES` before
   `build` go in four pull requests, `steward_evidence.STAGE_PULLS`: discovery (`start`, `vision and discovery`,
   `scope`), design (`prototype and design`), technical design (`stack and technical design`) and plan (`plan`). Each is
   on its own branch from the default branch and merged before the next stage starts. The stack options and the
   accepting commits of `stack-accept` stand on the same technical design branch.
2. **Every check and every yes stays.** Governance runs on each push of a stage; a later step reads its records from the
   work tree. Each approval names its head and is tied to its own record's digest, so a later push never voids an
   earlier approval of another record, and a fix to an approved record asks its approval again. The person's design
   approvals (SPEC-0037 rules 3 and 9), the architect's choice (SPEC-0029 rule 5), the plan approval (SPEC-0043 rule 8),
   the scope lock and the solo steward's recorded yes (SPEC-0062 rules 13 and 14) are unchanged.
3. **The setting** (`config.stage_pulls`, `common.plan_settings`). `"stage"` or `"step"`; absent is `"step"`, one pull
   request per step as before, so an upgrade changes nothing. Another value is refused naming `plan.stage_pulls`, never
   the value. `review_mode`, `execution` and personal mode change nothing here; in personal mode a stage is a set of
   commits in the sidecar.
4. **The texts.** The guide's "From an idea" names the four stages and their yes points; `skills/stack/SKILL.md` step 4
   lets the accept follow on the same branch; `skills/start/SKILL.md` and `skills/vision/SKILL.md` let the day-zero
   record join the discovery pull request. The one-pull-request-per-step wording of the guide and the skills is replaced
   by the `"step"` value.

## Consequences

About four merges come before the first build instead of about ten, each stage reviewed once as a whole, with the same
records, checks and approvals. No approved spec rule names one pull request per step of the first pass, so no amendment
is proposed; SPEC-0037 rules 3 and 9 still govern later changes. The setup's question that writes `"stage"` for a new
project is not part of this decision's build.

## Residual

The steward's setup does not yet ask to write `"stage"`; a project sets it by hand.

# ADR-0122: spec approvers, the clearance rule and the Approval line (REQ-039 build (c), SPEC-0032 rules 2, 5 and 6)

- Status: Accepted
- Date: 2026-10-25
- Deciders: maintainers
- Related: ADR-0115, ADR-0118, ADR-0110
- Requirements: REQ-039

Protected classes: `.claude/`, `.github/`, `config/`, `kit/`, `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`

## Context

SPEC-0032 (Approved, #187) rule 5: a person approves every spec. In the parallel run of 2026-10-24/25 the conductor's `Final:` lines set three specs to Approved (SPEC-0029, SPEC-0030, SPEC-0031), so an agent approved
requirements. This is build (c) of rule 13, from the default branch after the router (#193) and `watch` and `queue` (#197). The number ADR-0122 was reserved on #179 by the conductor, with two additions from the
experience of #187 and #196: `Approve:` is read from review bodies as well as comments, and the router sets `agk:approve` on an `Approval:` line. The tests were written first
(`tests/kit/test_spec_approvers.py`; before the code 21 of its 24 cases failed).

## Decision

1. **`spec_approvers`** in `config/reviewers.yaml`: a flow list of GitHub user handles (`scripts/agk/reviewers.py` `approvers_of`, `spec_approvers`). Absent, empty, a team handle or any other value lists nobody, and the
   installed placeholder `@REPLACE-ME` is never listed. `reviewers.py --check` fails a list that is not user handles, naming the setting and never a handle; an absent list passes (nobody may approve a spec). This
   repository lists `gbvraju`. The kit templates `reviewers.yaml` and `reviewers.adopt.yaml` are not changed (a changed template makes `upgrade` print a re-render hint in every project, and an absent list
   already approves nobody); the guide tells a project to add the line.
2. **The approval line** (`reviewers.py` `person_approvals`): the first line `Approve: <sha> SPEC-<n>` of an issue comment or of a review body, by a listed approver. The sha need only be hexadecimal, 7 to 40
   characters (the approval of #187 named an earlier head than the one cleared). A review counts whatever its state: the line approves, not the review button. Any other account, line or form counts for nothing.
3. **The clearance rule** (`scripts/agk/check_final_clearance.py`, `--reviews FILE`): when the latest verdict by a listed author is a covered fix list with a `Final:` line that sets `docs/specs/<nnnn>-*.md` to
   `Approved`, the spec needs a person's approval line; without it the check fails, naming rule 5 and `spec_approvers`, never a spec or a handle. `.github/workflows/governance.yml` writes `reviews.json` beside
   `comments.json` (one more read-only GET, `pull-requests: read`) and passes it. `Final:` lines for ADRs and requirements are unchanged.
4. **The conductor** (`.claude/agents/conductor.md`): for an intake it ends its verdict with `Approval: SPEC-<n> <path> Draft -> Approved, waiting for a person`, writes no `Final:` line for a spec until the
   person's line exists, and never writes `Approve:`. The role file is the boundary until the identities are separated (SPEC-0032 rule 6).
5. **The router** (`scripts/agk/route.py`): `agk:approve` is set when the latest verdict by a listed author that names the head has an `Approval:` line whose spec has no approval line of a listed person, and that
   state comes before `agk:fix` (the order is conflict, ci-running, ci-red, approve, fix, ready, review). The reader of `spec_approvers` and of the approval line is the one of `reviewers.py`, not a second copy.
6. Amendment 62 (`docs/runs/proposed-spec-amendments-62.md`) is applied to SPEC-0021 (the clearance rule), SPEC-0030 rule 6 and SPEC-0032 rule 2. The guide ("Running the loop") says how a person approves. A flow-mode
   fragment `changelog.d/req-039-c-approvers.md` records the change.

## Readings taken where the spec leaves a point open

Recorded as questions in the pull request, the most conservative reading each: this repository's `spec_approvers` is `gbvraju`, the user handle of the maintainers; a GitHub "Approve" review counts only with the
`Approve:` line in its body (the button alone names no spec); an absent `spec_approvers` fails nothing in `reviewers --check` but approves nobody; the check fails on the latest covered fix list only (a spec flip
in a pull request without one is a person's review, not this check's).

## Consequences

- A conductor or builder session can no longer approve a spec through a `Final:` line: the check fails the pull request until a listed person posts the line.
- A project that upgrades must set `spec_approvers` before a spec of its own can be approved through the loop; until then `agk:approve` waits.

## Residual

- 2026-10-25: sessions and people share one account until lane F (ADR-0117), so `spec_approvers` listing that account lets any session post `Approve:`; the role file forbids it and the shadow review is the check (due 2026-12-31).
- 2026-10-25: the conductor's guard hook does not refuse a comment whose first line is `Approve:`; the role file only forbids it (due 2026-12-31).

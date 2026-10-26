# ADR-0150: an approval an agent posted never counts (REQ-039, brief 242, SPEC-0032 rule 5)

- Status: Accepted
- Date: 2026-10-26
- Deciders: maintainers
- Related: ADR-0132, ADR-0149
- Requirements: REQ-039

Protected classes: `agk.toml`, `kit/`, `scripts/agk/`, `tests/kit/`

## Context

Brief #242 (priority 1, measured 2026-10-26 in this repository): many people run AGK alone, on one GitHub account that their agent sessions also use, and paid extra accounts are often not available. The approver lists name logins, so on one account an agent's `Approve:` looks like the person's. GitHub records the difference itself: a comment posted through a GitHub App carries `performed_via_github_app`. Every `Report:` and `Verdict:` of the cloud sessions on #233 reads `claude` there; the maintainer's `Approve:` on #223 (comment 6403609706), posted from the phone, reads null. Reviews: a review record (the one found, on #187) has no such field. The tests were written first.

## Decision

1. **The setting.** `agk.toml` gains `agent_apps`, a list of app slugs, default `["claude"]` (`common.agent_apps`; slugs are read case-blind; an empty list is allowed; any other invalid value is refused naming the setting and never the value). The two kit templates carry the default with a comment.
2. **The rule** (`reviewers.py`, `via_agent`). In every place a person's approval is counted (`approval_shas` and `person_approvals`, read by the router, by `check_specs.py --comments/--reviews` and by `check_final_clearance.py`) a comment whose `performed_via_github_app.slug` is in `agent_apps` never counts. A listed approver's login is still required. It is the same rule with one account or several, so no mode switch.
3. **Reviews** (the ruling on Q-242-1, option (b)). The record of a review shows no app, so it cannot show that an agent's app did not post it; an agent that submits a review through the same app on one account would look like the person. While `agent_apps` is not empty, a review never counts as a person's approval. With `agent_apps = []`, reviews count as before. The cost: a person's approving review stops counting by default; the person posts `Approve: SPEC-<n>` as a comment from their own account.
4. **Visible, not silent** (`route.py`, `correct_approvals`, the reply path of ADR-0149). An `Approve:` comment of a listed approver that was posted through a listed app gets one reply `Correction needed: an approval posted through an agent's app does not count; the person posts it themselves (approval comment <id>)`. A review of a listed approver that would have counted gets one reply that asks for the `Approve: SPEC-<n>` comment from their own account (approval review <id>). At most once for each comment or review, found by the marker; no label depends on it. An invalid `agent_apps` stops the router before it reads or writes anything.
5. **Role names stay as they are.** The first-line markers (`Verdict:`, `Report:`, `Request:`, `Assign:`) and the session names keep roles readable; they are not proof, and the security guide says so. It also states the limit: the field exists when an agent posts through an app, as cloud sessions do; a session on a person's own machine that uses that person's `gh` login posts with no field and looks like the person. The getting-started guide says what changes for reviews.
6. Existing tests of review approvals now set `agent_apps = []`. Amendment 85 (`docs/runs/proposed-spec-amendments-85.md`) is applied to SPEC-0032 rule 5. Flow mode: fragment `changelog.d/agent-apps.md`; no version bump.

## Consequences

- With one account, an agent that posts through its app can no longer approve a spec in the person's name; the person's own phone or web comment still counts.
- A project whose approvers approve through the review button must post the comment instead, or set `agent_apps = []` and accept that an agent's review looks like theirs.

## Residual

- 2026-10-26: an agent that posts with a person's own token, not through an app, still looks like the person; only the person's choice of how agents run closes it (due 2026-12-31).

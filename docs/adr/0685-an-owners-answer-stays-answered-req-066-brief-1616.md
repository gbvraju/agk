# ADR-0685: An owner's answer stays answered (REQ-066)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: brief #1616, found bug #1578, brief #1534 (ADR-0646), brief #1567 (ADR-0657), brief #1163 (ADR-0495), SPEC-0039 rule 4
- Requirements: REQ-066

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The owner wait (ADR-0646) keys an `Owner needed:` by its Q id only when a `Question:` with that id is already open, else
`owner-needed`; an answer pops only the Q id, so `owner-needed` stayed open and the pull request was parked again
(#1572 after `Maintainer answer: Q-1567-1`; #1609 parked 28 seconds after its unpark for `Q-1586-4`; #1610 and #1611).
An `accept <sha>` counted only on the exact current head (Q-1534-2), so a merge of main moved the head and parked #1576
again after the owner's accept of its pre-merge head.

## Decision

1. `session.open_owner_items` remembers the Q ids that the newest `Owner needed:` of each key names, in its first line
   or body. A `Maintainer answer: Q-<id>` or `Answer: Q-<id>` by an answerer closes the item keyed by that id and every
   open owner item that names it, `owner-needed` included. An answer to another id closes nothing (brief #1534
   answer 3), and an `Owner needed:` posted after the answer is open again.
2. `open_owner_items`, `owner_step` and `owner_apply` take an optional `carried(old, head) -> bool`. `accept <old>`
   closes the items when OLD is the head, or when `carried(old, head)` holds. `session.carried_check(root)` is the
   git-backed check: every first-parent step from OLD to the head (at most 20) satisfies `session_plan.light_merge`
   with `origin/<default_branch>` and `[flow] shared_indexes`. It never fetches; a commit that is not in the checkout,
   a bad setting or any failed read is False, so nothing is carried. The conductor's sweep and owner pass, the
   steward's park and unpark, `watch`'s park and the router's unpark pass it; the router has only the default branch,
   so it carries only what it can read (the maintainer answer to Q-1616-2), and the conductor's pass covers the rest.
3. The merger's evidence accept (`merge_cleared.answered`, SPEC-0039 rule 4) stays exact to the head (the maintainer
   answer to Q-1616-1). A carried accept ends only the owner wait, never a hold of the merger; the conductor still
   reviews the new head. A `Correction:` keeps its rule.

Settings: `[flow] owner_wait_minutes`, `owner_rest_hours` and `owner_utc_offset` are read and refused as before
(`config.owner_wait_settings`). `[flow] shared_indexes` decides what is a light merge; a bad value is refused
(`INDEXES_REFUSED`) and carries nothing. `review_mode` `team` and `solo` use the same answerers; another value is
refused by `common.review_mode`. `execution` `hosted`, `hybrid` and `pool`: the router unparks; `local`: the
conductor's pass parks and unparks; another value is refused by `common.execution`. `pr_mode`, `auto_merge`,
`reprove_paths` and `[steward] auto_file` are unchanged. `[personal] forge = "files"`: no pull request comments, not
applicable.

## Consequences

An answered question no longer parks a pull request again under `owner-needed`, and an accept survives a merge of main
that adds nothing beyond the default branch's change. A merge that changes one of the pull request's own files,
conflicts, or cannot be read still needs a fresh accept.

## Residual

- A merge of main that shares no file with the pull request is `none`, not `light`, by `reprove_kind`, so
  `light_merge` (as the brief names it) does not carry an accept over it: Q-1616-3 on the pull request.

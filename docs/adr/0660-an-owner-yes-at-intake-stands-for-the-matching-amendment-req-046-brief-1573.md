# ADR-0660: The owner's yes on a brief's answers stands for the amendment that matches them (REQ-046, REQ-066)

- Status: Proposed
- Date: 2026-11-20
- Deciders: maintainers
- Related: SPEC-0039, SPEC-0059, SPEC-0062, amendment 192, amendment 193, brief #1573, brief #1555, amendment 190, ADR-0653, amendment 170, amendment 124, plan #661
- Requirements: REQ-046, REQ-066

Protected classes the builds of this decision change: `scripts/agk/`, `.claude/`, `skills/`, `tests/kit/`, `kit/` and
`config/` (the reference lines only, when a build names them). This pull request changes none of them.

## Context

On the default branch at 90bf2753 (2026-11-20) an owner who already decided a brief's answers is asked again when the
amendment that writes them up lands. Brief #1555 held the owner's answers; its pull request #1565 added amendment 190
and ADR-0653; the conductor then posted `Owner needed:` (comment 7030183356), the owner posted
`Maintainer answer: amendment 190 approved` from their own account (comment 7030298350), and #1565 merged as 0d0e6266:
one more owner action and a 7.5-minute wait for a decision already made.

What holds it in the code: `route.py` `asks_owner` (line 502) keeps `agk:question` while an `Owner needed:` by a listed
verdict author has no later `Maintainer answer:` or `Approve:` by an account in `spec_approvers`, by login only;
`merge_cleared.py` holds `owner ask (rule 5)` on that label (line 1152, amendment 170), and `owner_only` (line 1166)
does not lift it. Spec approvals are separate: `merge_cleared.py` `unapproved` (line 959) and `same_text` (line 907,
amendment 124) hold an `Approval: SPEC-nnnn` line until a spec approver's `Approve:` names the head's text, and
`reviewers.py` `approval_shas` (line 297) never counts a comment posted through an app of `agent_apps`.
`steward_owner.py relay` (line 158) already posts `Maintainer answer: <Q> <answer>`, the `Owner said` line and
`Who: ProductOwner`, and its first-line form `Q-\d+-\w+` already accepts a `Q-<brief>-intake` id.

The owner's yes is only a yes by SPEC-0062 rule 14: one explicit sentence of approval in reply to the one question just
asked. A word to file ("file it") or a question is not one, so the yes has to be asked for when the brief is filed.

## Decision

1. SPEC-0059 changes only through amendment 193, and SPEC-0039 only through amendment 192, which this intake writes
   and does not apply. Each is applied word for word by its build, on the owner's `Approve:` of that spec.
2. **The ask (amendment 193 item 1).** When the steward files or drafts a brief whose `Touches:` names an Approved spec
   or whose `Adds:` names a `proposed-spec-amendments` file, it asks the owner one plain question after the brief text
   is final, showing the decisions in three lines or fewer. Only an explicit yes by SPEC-0062 rule 14 records anything.
3. **The record (amendment 193 item 2).** On the yes, one comment on the brief:
   `Maintainer answer: Q-<brief>-intake approved at intake: answers <list>; text sha256 <64 hex>`, then
   `Owner said (<UTC time>): "<verbatim>"`, then `Who: ProductOwner`, posted by `steward_owner.py relay --intake`. The
   hash is of the brief body's `Answers:` section with LF line ends and trailing spaces removed. In solo mode the
   steward's relay counts, as a relayed `Maintainer answer:` counts today (SPEC-0062 rule 13); in team mode only the
   approver's own post counts (SPEC-0062 rule 15), never one through an app of `agent_apps` (Q-1573-1, the brief's
   Q-1, on its recommendation).
4. **The amendment names its record (amendment 192 item 5).** The amendment file carries one line
   `Approved at intake: #<brief> comment <id>; answers <list>; sha256 <hex>`, and each numbered item ends
   `(answer <n>)`. `check_specs.py` checks the line's form only, with no network.
5. **One check (amendment 192 items 1 to 3).** `reviewers.py` `intake_approval(pull, brief, comments, files,
   approvers)` returns `agrees` or `differs: <reason>`, failing closed on anything unreadable, by the seven conditions
   of amendment 192 item 1. On `agrees` the conductor posts no `Owner needed:` for the amendment's approval and its
   verdict carries `Intake approval: agrees, #<brief> comment <id>`; `merge_cleared.py` re-runs the function before the
   merge and never trusts the verdict's line alone. On `differs` the hold `owner ask (rule 5)` stands as today, and the
   conductor's `Owner needed:` names only what differs.
6. **What the record never is.** Never an `Approve:` line, a verdict or a confirmation; never a spec approval: the
   `Approve: SPEC-<n>` of the build that applies the amendment stays the approver's own line (Q-1573-2, the brief's Q-2,
   on its recommendation). It lifts no release, protected-class, red-branch, pause, conflict or depends-on hold, and it
   changes no workflow, ruleset, required check or `agent_apps`.
7. **Withdrawal.** A later `Correction:` or `Maintainer answer: Q-<brief>-intake withdrawn` on the brief by an account
   in `spec_approvers` ends the record; a withdrawn or broken record is noted as a `Gap:` in the steward's memory.
8. In planning the steward still sends every requirement question to the owner (SPEC-0059 rule 3); the record only
   spares the second ask of a decision already made.
9. The builds (a) to (d) of the brief follow by the `brief` skill, each from the default branch, tests first; none
   changes a workflow.

## Consequences

- A brief with no record, and every project that never asks at intake, sees no change: the owner ask is held as today.
- On a matching record, an intake pull request like #1565 merges with no second owner action; an amendment that drifts
  from its answers is asked about only where it drifts.
- The merger gains one GET of the brief and one page of its comments for a pull request whose body names a brief.
- A spec approval of a later build is unchanged, so the third owner action of #1555's case stays.

## Residual

- (due 2026-12-20) Measure, after build (c) merges, how many owner asks the record spared and how many `differs` it
  raised; propose Q-1573-2's spec-approval step only from that measure.

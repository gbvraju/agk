# ADR-0647: The owner merges a held pull request by one comment, and a button merge is recorded (REQ-046)

- Status: Proposed
- Date: 2026-11-19
- Deciders: maintainers
- Related: SPEC-0039, amendment 185, brief #1539, ADR-0570, ADR-0354, ADR-0546, #1521, #1522, #1525, #1536, plan #661
- Requirements: REQ-046

Protected classes the builds of this decision change: `scripts/agk/`, `tests/kit/`, `.claude/`, `config/`, `.github/`,
`agk.toml`, `kit/`. This pull request changes none of them.

## Context

On 2026-11-19 the owner, on a phone, merged #1522, #1525 and #1521 with the forge's merge button. Their squash commits
(5bbf1618, deda2133, ea420a7f) carry no `ADR-nnnn Accepted (Final <id>)` line and no `Merged-by: merge_cleared.py`, so
`common.final_records` and `merger_records` see nothing, no `Auto merge:` line was posted, and ADR-0616, ADR-0639 and
ADR-0643 still read `Proposed`. The owner's merge through the kit, `merge_cleared.py --pr <n> --owner` (ADR-0570
decision 2), is refused inside an agent session and needs a terminal: a phone has none. An owner-only hold
(`OWNER_HOLDS`) has no phone path, and an accepted local head waits for the conductor's next `merge-queue` pass, which
runs only while a conductor session is awake. The merger job already starts on `issue_comment` events and the
supervisor's scripted pass already reads changed comments every `[autopilot] interval_minutes`. The owner prefers events
to polling (2026-11-19).

## Decision

1. The owner's word (SPEC-0039 rule 5b of amendment 185): a created comment on pull request `<n>` that is exactly
   `Merge: #<n> <40-character head>`, by a `User` account in `spec_approvers` that is a maintainer and is not in
   `conductor_accounts`, not through an app, with no `Who:` line or generator footer, and newer than the clearing verdict
   on that head. It lifts `OWNER_HOLDS` for that head only and never stands for a verdict or for the local-evidence
   accept.
2. One new form of the guarded command reads the word and runs the `--owner` path on its head, with every other hold,
   the would-be merge and the post-merge steps unchanged, adds `Merge-word: <comment id>` to the squash message before
   `Merged-by: merge_cleared.py`, and posts one `Merge done:`, `Merge held:` or `Merge refused:` reply per word and
   reason. Its trust is the person's word, not the terminal, so unlike `--owner` it is not refused for `SESSION_MARKERS`.
3. Three callers run it: the merger job on the comment event in hosted mode (option A), the supervisor's scripted pass
   in local mode (option D), and the conductor's `merge-queue` batch (option C). The `merge-cleared` lock and the pinned
   sha stop a second merge. The router (option B) is not a caller; it carries the hand-merge record on `closed`.
4. A merge into the default branch without `Merged-by: merge_cleared.py` is a hand merge: the router on `closed`
   (hosted) or local `git log --first-parent` (local) posts one `Hand merge:` line on the record issue and one `Owner
   needed:` per Proposed ADR the pull request added or changed. Nothing is reverted or accepted by the record.
5. Every role guard and `data_guard.py` deny a comment whose first line starts `Merge:`, `session.py tell` refuses it,
   and session rule 29 gains one sentence saying a session never posts or relays one.
6. This changes ADR-0570 decision 2: the owner's merge is `--owner` at a terminal or the word of decision 1. ADR-0570
   decision 1 and its other decisions stand. Principle 2 is unchanged (Q-1539-1).
7. The work is four builds, each filed by the `brief` skill: (a) the reader and the form, (b) the callers, the guards
   and the texts, (c) the hand-merge record and `doctor.py`'s shared-account warning, (d) the merger job's `if:`, a
   workflow change the owner makes and merges.

## Consequences

The owner merges a held pull request from a phone with one comment, through the same checks as `--owner`, within one
event (hosted) or one pass (local), and the merge carries its `Final:` lines and record. A button merge no longer leaves
ADRs silently Proposed. In personal mode nothing changes but the guards' denial. A build that cites this ADR with
`Covered-by:` once it is Accepted may change only the classes named above; build (d) changes `.github/` and is held for
the owner.

## Residual

- 2026-11-19: with one account for the owner and the sessions, GitHub cannot tell a `Merge:` comment the person typed
  from one a session posted; the guards and session rule 29 hold it, as for `Confirmed:`; `doctor.py` warns of the
  shared account (due 2026-12-31).
- 2026-11-19: a hand merge's skipped would-be merge and governance run are not re-run by the record (due 2026-12-31).

# ADR-0723: An approval ask offers a line for the pull request's own spec

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1735, brief #1733, brief #1656, brief #1534, ADR-0690, ADR-0722, ADR-0543, ADR-0710
- Requirements: REQ-039, REQ-050

Protected classes: `scripts/agk/`, `tests/kit/`, `.claude/`

## Context

`route.APPROVAL_ASK` (ADR-0690) matched `Approve: SPEC-<nnnn>` or `Maintainer answer: amendment <n> approved`
anywhere in an `Owner needed:` body, and `route.owner_ask` and `session.open_owner_items` closed every open item on
any `Approve:` or `Maintainer answer:` by an answerer. On 2026-11-22 the owner posted `Approve: SPEC-0050` on #1723,
which does not change SPEC-0050. The conductor's `Owner needed:` that said so quoted the line, and the router
labelled #1723 `agk:approve`. A merge ask that recaps an approval inline lost its `agk:owner-merge` state
(ADR-0722) and was parked, and a misplaced `Approve:` closed an open owner question.

## Decision

1. ADR-0690 is changed: `route.approval_ask(body, files)` returns the approvals an `Owner needed:` asks for. A line
   of the body counts when, stripped of spaces and of one wrapping pair of backticks, it is exactly
   `Approve: SPEC-<nnnn>` or `Maintainer answer: amendment <n> approved`, and the pull request changes that spec's
   file (`docs/specs/<nnnn>-*.md`) or `docs/runs/proposed-spec-amendments-<n>.md`. A line inside a sentence or a
   quote, or one for a spec or amendment the pull request does not change, asks for nothing. When the changed files
   cannot be read (None), every match anywhere in the body counts, as before (brief #1735 Q-1).
   `route.owner_ask` and `session.open_owner_items` both use it (imported, not copied).
2. An `Owner needed:` that asks for nothing is an owner question (`agk:question`), or a merge ask (ADR-0722) when it
   names `merge_cleared.OWNER_COMMAND` for the pull request: a recap of an approval inside a merge ask no longer
   turns it into an approval ask.
3. An approver's `Approve: SPEC-<nnnn>` (with or without a sha) or `Maintainer answer: amendment <n> approved` on a
   pull request that changes neither that spec nor that amendment closes nothing. Placed on its own pull request,
   it closes the approval it names; while another asked approval stays open the state stays `agk:approve`, and
   when none stays open it closes as before (every item, with ADR-0722's rule for an open merge ask). Every other
   answer line is read as before; when the files cannot be read, an approval line closes as before.
4. The conductor's owner-merge `Owner needed:` names only `python3 scripts/agk/merge_cleared.py --pr <n> --owner`,
   with `merge_queue` on too, never the Merge button, which leaves out the acceptance record. A misplaced approval
   or answer line gets one comment whose first line is `Note:`, naming the pull request where it belongs; no reader
   counts it.
5. `session.owner_apply` decides on its fresh read, which now also reads the pull request's changed files; the
   caller's own read skips no step when a comment names an approval line, because that read has no files.

## Consequences

A note or a recap never relabels a change or closes another question, and an approval answers only on the pull
request that changes its spec. One more GET (the changed files) per fresh owner-wait read.

## Residual

- 2026-11-22: ADR-0712's acceptance record, lost by the button merge of #1719, is not repaired here (brief #1735
  Q-3: a separate brief).

# Proposed spec amendments 170 (SPEC-0039; REQ-039)

Date: 2026-11-12 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0483 (brief #1134), which stays `Proposed` for the maintainers' decision. The path (rule 5):
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The numbers 170 and 0483 are
the ones brief #1134 reserved. The owner decides it with `Approve: <head> SPEC-0039` on the pull request; no session posts
that line.

The sentence (brief #1134): "The merger never merges a pull request while an owner's answer or a spec approval it waits
for is still open, even after the conductor has asked the owner on that pull request."

## What is on the default branch today

Read in the code by this session on `origin/main` (0430b9d):

- `scripts/agk/route.py` `base_state` returns `agk:question` for an open `Owner needed:` before it reaches the
  `agk:approve` state, so a pull request that needs a spec approval and carries an owner ask is labelled `agk:question`.
- `scripts/agk/merge_cleared.py` `unapproved` holds only on the label `agk:approve` or an `Approval: SPEC-nnnn` line of
  the pull request's body; it never reads the clearing verdict's `Approval:` line, and no hold of rule 5 names
  `agk:question`.
- Measured (brief #1134): #1132's verdict carried `Approval: SPEC-0030` and a `Final:` line; the router labelled it
  `agk:question`; merger run 43283562751 printed `merge-cleared #1132 c224b6b927e0: merged c26da3f87e77` with no
  `Approve: SPEC-0030` on it.

## Items

1. **Rule 5, the `spec approval` item, one added sentence.** "The `Approval: SPEC-nnnn` lines of the clearing verdict
   (the latest `Verdict:` by a listed verdict author naming the head) are read beside the body's, exactly as the body's
   are read, amendment 124 included (`spec approval`)."
2. **Rule 5, one added item after `hold label`.** "- one labelled `agk:question`, an open owner ask, whatever the ask
   is (`owner ask`);"
3. **`--status`.** "Both are reported as pending the same way: `owner ask (rule 5)`, and `approve SPEC-nnnn` naming the
   first spec of the body's or the verdict's lines that has no approval for the head."
4. **Tests.** `tests/kit/test_merge_cleared_owner_ask.py`: a cleared head labelled `agk:question` is held naming
   `owner ask`; a covered fix list whose verdict carries `Approval: SPEC-0030` and no `Approve:` is held naming
   `spec approval`, and merges once a spec approver's `Approve: <head> SPEC-0030` names the head; a verdict without an
   `Approval:` line and no owner ask merges; an older verdict's line does not hold; `--status` prints both pendings.

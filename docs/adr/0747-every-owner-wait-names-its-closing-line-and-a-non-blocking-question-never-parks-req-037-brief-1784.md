# ADR-0747: Every owner wait names the line that ends it, and a question both sides call not blocking never parks (REQ-037)

- Status: Accepted
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1784, ADR-0543, ADR-0685, ADR-0722, ADR-0723, ADR-0749, plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `.claude/`, `tests/kit/`, `config/`, `agk.toml`

## Context

Three waits on the owner in one day were caused by lines no reader closes or by reads that cannot tell two cases
apart. On #1762 the conductor asked for the size word in free text ("for example `Size accepted`"); the owner's
`Size accepted.` matched no line of `session.open_owner_items`, so the pull request stayed parked with every check
green. Later the owner's `Maintainer answer: accept <sha>` was lost again after a merge of main touched a file the
pull request also changed: `carried_check` carries an accept only across a light merge. On #1773 the builder's
question said in its text that it did not block, both verdicts agreed, and `for_the_maintainers` still read it as a
wait, so a cleared head was parked for 4 hours 44 minutes. The owner's word (2026-11-23, the steward chat, quoted as
data): "Yes, brief the size-accept and non-blocking-park fix".

## Decision

1. `session.closing_line(key, pr, comments)` is the one source of the line that closes each kind of owner item: a Q
   id (also `nb:<Q-id>`) `Maintainer answer: Q-<id> <your answer>`; `owner-needed` `Maintainer answer: accept <full
   head sha>`; `approve` the newest approval line the comments offer (`route.APPROVAL_ASK`), else the
   `route.APPROVAL_LINE` form; `owner-merge` `merge_cleared.OWNER_COMMAND` of the number, a command the owner runs,
   not a comment. `session.py ask-lines --pr N` (GET only) prints `<key>: <line>` for each open item, or `none`.
2. `conductor.py check-verdict FILE --pr N` refuses an `Owner needed:` body that holds no line which, posted by an
   answerer, closes the item the ask opens, read by `open_owner_items` itself: `refused: an Owner needed: names no
   line that closes it (setting: Owner needed:)`. The conductor's role file has every ask above a standing ruling end
   with the `ask-lines` line, verbatim, on its own line.
3. A non-blocking question has one form, `Question: Q-<id> for the maintainers (not blocking): <text>`, named in the
   builder's role file. `open_owner_items` keys it `nb:<Q-id>` only while the newest verdict by a listed author on
   the current head (or on an older head whose change `carried` holds to it, decision 5; `Q-1784-2`) names that Q id
   with `does not block` or `not blocking` on its `Answers:` line, no other line; otherwise it is
   an ordinary question keyed by its Q id and parks as today. A builder alone never exempts its own question.
4. `owner_step` never parks for an `nb:` item and never hands over for one; it stays listed by `ask-lines` and by
   every reader of `open_owner_items` until answered. A park this rule wrote for a question that is now `nb:` is
   lifted with one `Unparked-by: not-blocking Q-<id>`, which `UNPARKED_BY` reads and `ANSWER_UNPARK` does not (it
   is not owed to a builder). A person's own park is never removed. `merge_cleared.py` is unchanged.
5. `carried_check`'s `carried(old, head)` also holds when every first-parent step from OLD to HEAD is a merge whose
   second parent is on the default branch and the pull request's own diff is unchanged: the `git patch-id --stable`
   of `git diff <merge-base> <old>` equals that of `git diff <merge-base> <head>`, each against its own merge base
   with the default branch. A merge that resolves a conflict inside the pull request's own lines changes the patch
   id and carries nothing.
6. A plain `Size accepted` stays text and closes nothing (`Q-F1-1`, the conservative reading); the steward relays it
   as the `ask-lines` line. `[flow] owner_wait_minutes`, `owner_rest_hours`, `auto_merge`, `review_mode` and
   `pr_mode` keep their readings; none of them parks an `nb:` item.
7. In personal mode (`forge = "files"`, `Q-1784-1`, the steward's answer) no park or label exists; `ask-lines` reads
   the sidecar's `forge/pulls/<n>.json` and `forge/comments-<n>.json`, posts nothing, and counts an answer line only
   as `reviewers.derived_only` derives it, so a plain comment in a sidecar answers nothing.

## Consequences

An owner who answers with the printed line is read at once, a question both sides call not blocking no longer parks
a cleared head, and an accept survives a merge of main that leaves the change itself the same. A test of brief
#1616 that expected no carry across a clean merge touching a shared file now expects the carry; one whose merge
changes the pull request's own diff expects none.

## Residual

- 2026-11-23: `steward.py refresh` and the conductor's hourly report do not read `open_owner_items`, so an `nb:` item
  is listed by `ask-lines` (and stays in the pull request's `Questions:`) but not there yet; a later brief may add it.

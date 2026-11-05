# Proposed spec amendments 117 (SPEC-0040; REQ-047)

Date: 2026-11-05 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0274 (brief #552), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0040-a-builder-hands-heavy-runs-to-a-first-in-first-out-queue-and-keeps-developing.md`. The number 117 is the one
the conductor reserved in its field note on #552 of 2026-11-05. Unlike 111, this amendment is applied to the spec text in the
same pull request, as that field note directs. It needs a person's `Approve: SPEC-0040` on the pull request; no session posts it.

The owner's direction of 2026-11-05 (the conductor's field note on #552), quoted as data: "we have decided priority based as
well ... if something is blocking bigger scope which can help move other builders or all builders fast that needs to be
treated, instead of putting in queue."

1. **Priority becomes the default (rules 1 and 5).** `queue_order` defaults to `"priority"`; `"fifo"` stays available and
   keeps its meaning word for word. Rule 1 reads "`queue_order` is `"priority"` (the default, amendment 117) or `"fifo"`";
   rule 5 drops "(the default)" after `"fifo"` and adds it after `"priority"`. This repository's queue stays off
   (`agk.toml` is unchanged). The kit's templates show `queue_order = "priority"` in their commented `[locks]` table.
2. **Unblockers go first (rule 3, read by rule 5).** At `submit`, a job's priority is raised by one level when its brief is
   named in a `Depends-on:` line of another open brief (an open issue labelled `agk-brief`) or open pull request, read once
   at submission like the brief's own `Priority:` line, and the job records `raised: unblocks #<n>[, #<m>]` in a `raised`
   field beside its `priority` (Q-552-4). A raise never takes a job to 0, which stays the red-default-branch brief's, so
   that brief stays first (Q-552-3); `unknown` is not raised; a read failure leaves the priority as read and raises
   nothing. A job that replaces another in place reads its brief, and so its raise, again.
3. **Unchanged.** A running job is never stopped or pre-empted; overdue jobs (`queue_max_wait`) still go first by sequence
   number; no gate is skipped; `fifo` orders by sequence number only, whatever the priority or the raise.
4. **Q-S0040-2.** Its ruling keeps its text, with "the default" after `"fifo"` read as "the default until amendment 117".
5. **Tests.** The rules 4 to 6 line: with `"fifo"`, jobs of priorities 3, 0 and 2 run in submission order, and with
   `queue_order` unset they run by priority. A new line under rule 5: a job whose brief blocks two open briefs or pull
   requests runs before an older job of the same written priority; the red-default-branch brief stays at 0 and first;
   with `"fifo"` nothing changes; a GitHub read failure raises nothing. They are in `tests/kit/test_lock_queue_runner.py`,
   marker `REQ-047`.
6. **REQ-047 AC3.** Its words "with queue_order unset or fifo it starts them strictly in submission order" no longer hold
   for an unset `queue_order`. `docs/requirements.md` is the maintainers' and is not changed here (Q-552-5).

# Proposed spec amendments 151 (SPEC-0039; REQ-046)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0387 (brief #853), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The number 151 is the one
brief #853 reserved. This amendment is not applied to the spec text in this pull request; the owner decides it, and it
needs a person's `Approve: SPEC-0039`; no session posts it. It reads with amendments 144 and 148.

1. **Rule 2, the verdict as a commit status.** Add: "`merge_cleared.py --status --pr <n> --sha <head>` sets the commit status
   `agk/verdict` on that head by the reading of the merge: `success` when the head is cleared, no hold of rule 5 stands and
   it is not in the re-prove state of SPEC-0050; otherwise `pending` with the reason (`fix list`, `approve SPEC-nnnn`,
   `re-prove <file>`, `owner merge`, or the hold's own words). A `--sha` that is not the head sets nothing. In local mode
   it prints the state and sets nothing."
2. **Rule 2, what starts the guarded command.** Add: "In GitHub mode with `auto_merge = true`, the commit status
   `agk/verdict` with `success` starts the merger job, as a condition of the existing job, on the one open pull request into
   the default branch with that head. The status starts the job and clears nothing: the guarded command reads the verdict
   again."
3. **Rule 5, up to date before merge.** Add: "The owner turns on `strict` in the ruleset, so that a pull request behind the
   default branch cannot merge. `doctor.py` warns when it is off with `auto_merge = true`."
4. **Rule 1, the merge queue.** Add: "`[flow] merge_queue = false | true` (default `false`) is for a project that can use
   GitHub's merge queue. With `true`, `agk/verdict` is a required status of the queue, the command holds naming the
   setting and the re-prove reading is the queue's result."
5. **Not in this amendment.** Rules 3, 4 and 6 to 11 are unchanged: only the guarded command merges, and it holds
   everything it holds.

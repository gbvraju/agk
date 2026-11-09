# Proposed spec amendments 148 (SPEC-0039; REQ-046)

Date: 2026-11-09 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0383 (brief #836), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`. The number 148 is the one
brief #836 reserved. This amendment is not applied to the spec text in this pull request; the owner decides it, and it
needs a person's `Approve: SPEC-0039`; no session posts it. It reads with amendment 144, which added the sweep.

1. **Rule 2, what starts the guarded command.** Add at the end: "In GitHub mode with `auto_merge = true`, a comment whose
   first line starts `Verdict:`, `Final:` or `Approve:` starts the merger job when it is created, and also when it is
   edited (a created `Final:` as before starts nothing): the job reads the edited body as it reads a new one."
2. **Rule 2, the sweep reads verdicts.** The sweep lists every open, non-draft pull request, oldest first, and runs the
   guarded command on those whose latest verdict clears the current head, by the reading of rule 3, at most five a run.
   A pull request's label is never an input. A cleared pull request labelled `agk:fix` or `agk:review` prints
   `LABEL #<n> <label> but cleared`, and the router is run for it when it is left unmerged.
3. **Rule 2, when the sweep runs.** The sweep runs after every finished `governance` or `proof` run, whatever its
   conclusion, after the event job of that run, and also on the schedule and by `workflow_dispatch` as a fallback. One
   sweep runs at a time.
4. **Rule 2, what the sweep prints.** For each pull request it merges the sweep prints the minutes from its clearing
   verdict, counted from the verdict's last edit, to the merge.
5. **Rule 9, a late sweep.** Add: "`conductor.py watch` prints `SWEEP late <m> min` when no sweep run finished in the last
   30 minutes and a cleared pull request is open."
6. **Not in this amendment.** Rules 3 to 8 and 10 are unchanged: the sweep merges only through the guarded command and
   holds everything it holds.

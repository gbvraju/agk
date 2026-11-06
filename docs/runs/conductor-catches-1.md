# Conductor catches 1 (operating lessons as evidence, brief #604)

Date: 2026-11-06 (from `date -u`). The architect catch logs (`docs/runs/architect-catches-N.md`) grow the review checklist from
evidence. This file does the same for the conductor's operating lessons: each incident of a conductor run is a row with the
strongest guard that prevents it, so that no lesson lives only in one session's notes (brief #604, ADR-0294).

## How the rows were checked

Rows 1 to 12 are the incidents of 2026-11-04 to 2026-11-06 that the owner's brief #604 lists; rows 13 and 14 are the two that
the conductor's fix list on the first head of its pull request added. Rows 15 to 22 are the incidents of 2026-11-06 that brief #695 lists:
its issue and pull request numbers (#643, #657, #659, #667, #669, #684) were read on GitHub; its timings rest on the brief. Each pull request and issue number was
read on GitHub (GET only). A detail that the record of this repository does not show (a time that lives only in a session) is
marked `(unverified)`; a cost that was not measured is `(unknown)`, never zero. Rows hold counts, timings and numbers only.

Kinds (fixed list): `watch` (a wait or a watch that missed an event, stalled or lapsed), `unread-result` (a result that was read,
but not in full, before reporting), `parallel-merge` (changes green alone and red together), `false-red` (a red that was not a
defect of the change), `kit-gap` (a kit rule that refuses a valid case), `history` (a fix that leaves the bad commit in the
branch), `sequence` (a step after the reviewed head), `stale-input` (a rerun that used an old input), `conflict` (a shared file
that every pull request touches). None of them is a kind of the architect catch logs, so no row here changes
`config/review-checklist.md` (brief #604 item 3).

Guard forms: `` check `<path>` `` (a check that fails the case), `` test `<path>` `` (a test that fails the case), `` rule `<path>` ``
(a line of `.claude/agents/conductor.md`, under "Operating lessons", that cites the row), `pending #<n>` (an open brief or a
merged pull request that builds the guard), `pending (to be filed)` (a guard whose brief is not filed yet). A row may hold several, separated by `; `, strongest first.

## The catches

| # | Date | Kind | What happened | Cost | Cause | Guard |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-11-05 (unverified) | watch | a builder's `Question:` on an issue was not seen by the watch; the default branch stayed red overnight | (unknown): overnight (unverified) | the watch read questions and reports on pull requests only | check `scripts/agk/conductor.py` (watch and sweep, brief #643); rule `.claude/agents/conductor.md` |
| 2 | 2026-11-05 (unverified) | watch | a merge script waited on a process name that matched its own command line | 25 min (unverified) | a wait on a name match, which matches the waiter itself | rule `.claude/agents/conductor.md` |
| 3 | 2026-11-05 (unverified) | unread-result | a `REAL RED` line in a merge log was not read before the merge was reported | (unknown) | the result was reported from its last line | check `scripts/agk/conductor.py` (merge-queue reads each result and stops at the first that is not a merge, brief #643 build (b)); check `scripts/agk/merge_cleared.py` (the red-branch issue holds merges, in force); rule `.claude/agents/conductor.md` |
| 4 | 2026-11-05 | parallel-merge | two pull requests passed alone and broke the default branch together (#581 built its test map before #579 merged; found on #597) | (unknown): the default branch red from #597 on | a map built before a sibling merged | check `scripts/agk/merge_cleared.py` (the after-merge governance run, in force); rule `.claude/agents/conductor.md` |
| 5 | 2026-11-05 | false-red | the after-merge governance run had no pull request body, so a `Covered-by:` merge was reported red (brief #576) | (unknown) | the run read no body | check `scripts/agk/merge_cleared.py` (#577, merged) |
| 6 | 2026-11-06 | kit-gap | `Covered-by:` refused an ADR accepted by a rule 3a `Final:`, and a rule 3a merge kept the `agk:fix` label (#577 and #581) | 2 merges (#577, #581) with the wrong label | the file of an ADR accepted by rule 3a says `Proposed` until the release | pending #601 |
| 7 | 2026-11-05 (unverified) | history | a fix commit was pushed on top of a commit that held a leaked literal; the secret scan reads every commit of the branch | (unknown) | a fix on top leaves the bad commit in the branch | rule `.claude/agents/conductor.md` |
| 8 | 2026-11-05 (unverified) | sequence | a fix list's `Final:` sequence ended two commits past the reviewed head and failed session rule 7 | (unknown) | the `Final:` commit came after commits that no verdict named | rule `.claude/agents/conductor.md` (in force: the cleared verdict names the head) |
| 9 | 2026-11-05 (unverified) | stale-input | a rerun of a check replayed the old pull request body after the body was fixed | (unknown) | a rerun reads the event of its first run | rule `.claude/agents/conductor.md` |
| 10 | 2026-11-05 | conflict | the append-only decisions log conflicted on every pull request that added a row | (unknown) | one file that every pull request appends to | check `scripts/agk/check_specs.py` (one file per entry, #558, merged) |
| 11 | 2026-11-05 (unverified) | kit-gap | a spec approval written with a trailing period was refused | (unknown) | the approval line is matched exactly | rule `.claude/agents/conductor.md` |
| 12 | 2026-11-05 (unverified) | watch | monitoring lapsed while the conductor was idle | 7 h (unverified) | the watch was not started again after a notification | check `scripts/agk/conductor.py` (watch and sweep, brief #643); rule `.claude/agents/conductor.md` |
| 13 | 2026-11-06 | watch | a builder's `Report:` on #616 at 07:43 UTC was seen at 09:15 UTC (the verdict on it at 09:16 UTC) because the watch had ended and was not started again | 1.5 h of a ready pull request waiting | no wake-up while idle | check `scripts/agk/conductor.py` (watch and sweep, brief #643); rule `.claude/agents/conductor.md` |
| 14 | 2026-11-06 | kit-gap | an owner's `Approve: SPEC-nnnn` without a sha counts for CI but not for `merge_cleared.py`, and a merge of the default branch after it needed a new sha approval though the spec text did not change (#592, #603, #616) | (unknown): 3 extra owner approval lines | the merge script reads only a sha approval of the current head | pending (to be filed) |
| 15 | 2026-11-06 | parallel-merge | #657 and #659 (two red-branch issues of the governance check): two pull requests, each green alone, were red together on the rule budget; merges were held (first of two) | 2 h of held merges (unverified; shared with row 16) | each pull request ran the budget test against the default branch without the other | pending #667 (the pre-merge check runs the kit's budget and map tests) |
| 16 | 2026-11-06 | parallel-merge | the same failure again on #659, after #657 | 2 h of held merges (unverified; the same 2 h as row 15) | the pre-merge check did not run the kit's budget test | pending #667 (the pre-merge check runs the kit's budget and map tests) |
| 17 | 2026-11-06 | watch | two builders (b649, b654) died before pushing and were noticed hours later | (unknown): hours (unverified) | no evidence of a live builder was read; the conductor waited | check `scripts/agk/conductor.py` (`SILENT` in the sweep, brief #669, closed) |
| 18 | 2026-11-06 | false-red | proof runs were cancelled by a push right after a pull request was marked ready | (unknown) | the new push cancels the runs of the head before it | pending (to be filed) (the conductor's rerun_cancelled outside the kit, later a kit command) |
| 19 | 2026-11-06 | false-red | a push to a ready pull request left only skipped runs | (unknown) | the runs of a push to a ready pull request are skipped | pending (to be filed) (draft, push, then ready, later a kit command) |
| 20 | 2026-11-06 | kit-gap | the builders' sandbox refused the secret scanner's download, so prepush could not pass | 1.5 h (unverified) | prepush required the scanner in a session that cannot install it | check `scripts/agk/prepush.py` (the deferral, ADR-0327, #684, merged) |
| 21 | 2026-11-06 | history | the conductor amended a pushed commit and attempted a force-push on `claude/brief-683` before its pull request existed; an ordinary push superseded it | (unknown) | a pushed commit was amended in the conductor's own checkout | pending (to be filed) (no amend after a push, own builds in a worktree) |
| 22 | 2026-11-06 | unread-result | the conductor's merge script read one page of check runs and waited on a green default branch | 40 min (unverified) | one page of check runs was read as all of them | check `scripts/agk/conductor.py` (merge-queue merges through `merge_cleared.py`, which reads every page of the check runs, brief #643 build (b)) |

## What this shows

Counted from the table and nothing else. 22 rows; 5 with their numbers verified on GitHub in full (rows 4, 5, 10, 13 and 14), 1 in part
(row 6: the issue and the merges, not the time), 8 that rest on the owner's account (`(unverified)`), and 8 of brief #695 (rows 15 to
22) whose numbers were read on GitHub and whose timings rest on the brief.

- **By kind:** `watch` 5 (rows 1, 2, 12, 13, 17); `kit-gap` 4 (rows 6, 11, 14, 20); `parallel-merge` 3 (rows 4, 15, 16); `false-red` 3
  (rows 5, 18, 19); `unread-result` 2 (rows 3, 22); `history` 2 (rows 7, 21); `sequence` 1 (row 8); `stale-input` 1 (row 9);
  `conflict` 1 (row 10).
- **By the strongest guard:** a check 10 (rows 1, 3, 4, 5, 10, 12, 13, 17, 20, 22, of which rows 1, 3, 4, 12 and 13 also carry a rule
  line; rows 1, 3, 12, 13 and 22 by `conductor.py`, brief #643; row 17 by `conductor.py`, brief #669; row 20 by `prepush.py`, #684);
  pending 7 (row 6, #601; rows 15 and 16, #667; rows 14, 18, 19 and 21, to be filed); a rule line only 5 (rows 2, 7, 8, 9, 11).
  No row has a test as its strongest guard.
- **Corrections of the given list:** row 1 named `pending #601` beside its rule; #601 builds the rule 3a gaps of row 6 and nothing
  about the watch, so row 1 keeps its rule line only. Brief #695 gives rows 18, 19 and 21 a practice as the guard; a `rule` guard
  needs a line of `.claude/agents/conductor.md`, which the brief does not touch, so they are `pending (to be filed)`.

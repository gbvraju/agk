# Conductor catches 1 (operating lessons as evidence, brief #604)

Date: 2026-11-06 (from `date -u`). The architect catch logs (`docs/runs/architect-catches-N.md`) grow the review checklist from
evidence. This file does the same for the conductor's operating lessons: each incident of a conductor run is a row with the
strongest guard that prevents it, so that no lesson lives only in one session's notes (brief #604, ADR-0294).

## How the rows were checked

Rows 1 to 12 are the incidents of 2026-11-04 to 2026-11-06 that the owner's brief #604 lists; rows 13 and 14 are the two that
the conductor's fix list on the first head of its pull request added; rows 15 and 16 are the two red default branches of brief #667. Each pull request and issue number was
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
| 3 | 2026-11-05 (unverified) | unread-result | a `REAL RED` line in a merge log was not read before the merge was reported | (unknown) | the result was reported from its last line | rule `.claude/agents/conductor.md`; check `scripts/agk/merge_cleared.py` (the red-branch issue holds merges, in force) |
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
| 15 | 2026-11-06 | parallel-merge | #638 and #648, each green alone, made the default branch red once both had merged (#657): `config/session-rules.md` 3523 words against the 3469-word budget line, the budget test 1 failed | 25 min of a red default branch (13:22 to 13:46 UTC); 1 fix pull request (#658) | the check before the merge ran governance only, not the kit test that reads the whole tree | check `scripts/agk/merge_cleared.py` (the pre-merge tests, brief #667); test `tests/kit/test_merge_cleared_pre_tests.py` |
| 16 | 2026-11-06 | parallel-merge | #644 and #648, each green alone, made the default branch red once both had merged (#659): `.claude/agents/conductor.md` 4570 words against the 4541-word budget line, the budget test 1 failed | 33 min of a red default branch (14:23 to 14:55 UTC); 1 fix pull request (#660) | the same as row 15, the second time on one day | check `scripts/agk/merge_cleared.py` (the pre-merge tests, brief #667); test `tests/kit/test_merge_cleared_pre_tests.py` |

## What this shows

Counted from the table and nothing else. 16 rows; 7 with their numbers verified on GitHub in full (rows 4, 5, 10, 13, 14, 15 and 16), 1 in part
(row 6: the issue and the merges, not the time), 8 that rest on the owner's account (`(unverified)`).

- **By kind:** `watch` 4 (rows 1, 2, 12, 13); `kit-gap` 3 (rows 6, 11, 14); `unread-result` 1 (row 3); `parallel-merge` 3 (rows 4, 15, 16);
  `false-red` 1 (row 5); `history` 1 (row 7); `sequence` 1 (row 8); `stale-input` 1 (row 9); `conflict` 1 (row 10).
- **By the strongest guard:** a check 9 (rows 1, 3, 4, 5, 10, 12, 13, 15, 16, of which rows 1, 3, 4, 12 and 13 also carry a rule line; rows 1,
  12 and 13 by `conductor.py`, brief #643); pending 2 (row 6, #601; row 14, to be filed); a rule line only 5 (rows 2, 7, 8, 9, 11).
  No row has a test as its strongest guard; rows 15 and 16 carry one after their check.
- **Corrections of the given list:** row 1 named `pending #601` beside its rule; #601 builds the rule 3a gaps of row 6 and nothing
  about the watch, so row 1 keeps its rule line only.

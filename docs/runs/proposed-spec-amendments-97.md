# Proposed spec amendments 97 (SPEC-0021, SPEC-0025, SPEC-0032; REQ-039)

Date: 2026-10-30 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is applied by
ADR-0179 (brief #277), which stays `Proposed` for the maintainers' decision, and it changes
`docs/specs/0021-when-a-fix-list-verdict-s-only-item-is-the-final-commit-and.md`,
`docs/specs/0025-a-team-can-run-independent-pull-requests-in-parallel-without.md` and
`docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md`. The number 97 is the next free one
(95 is held for brief #305); Q-277-4 asks the conductor to confirm it.

1. **SPEC-0021 rule 5, a new last paragraph: the solo confirmation.** "With `review_mode = "solo"` in `agk.toml` (the default is
   `team`), a comment whose lines are `Confirmed: <40-hex sha>`, then `Verdict: cleared|fix list|rejected <the same sha>`, then any
   lines, then `Shown:` and exactly three lines (the summary the person was shown), and last `confirmed by <login> in a session at
   <YYYY-MM-DDTHH:MM:SSZ>`, where the login is the comment's author, counts as the verdict of its second line, with its `Final:`
   lines, by its author, for the metrics, the router and the check. Whether the author is a listed verdict author is judged as for
   any comment. Any other shape, a confirmation whose verdict names another sha, and every confirmation in team mode count for
   nothing. A comment posted through an app of `agent_apps` never counts as a confirmation."
2. **SPEC-0021 rule 6, a sentence added.** "Solo mode needs exactly one person in `verdict_authors` and `spec_approvers` together:
   `reviewers.py --check` (governance) fails naming the setting `review_mode` when nobody or more than one person is listed."
3. **SPEC-0025 rule 4, a sentence added.** "Solo mode lists one person, so a confirmation by the pull request's own author counts,
   as any verdict does with one listed author."
4. **SPEC-0032 rule 5, a new last paragraph.** "In solo mode, each line `Approve: SPEC-<n>` between the verdict line and `Shown:` of
   a solo confirmation (SPEC-0021 rule 5) by an account in `spec_approvers` counts as `Approve: <confirmed sha> SPEC-<n>`: it approves
   the text at the confirmed sha, for the router, `check_specs.py` and `check_final_clearance.py`. One comment is then the verdict,
   its `Final:` lines and the approval together; the session makes the status commit right after it, alone, as today (rule 5's last
   sentence). In team mode such a line counts for nothing; the person still merges."
5. **SPEC-0032 rule 6, a sentence added.** "In solo mode the one person's account posts the confirmation through a session, so the
   residual of one account is the whole of solo mode: the confirmation's last line and its three summary lines record what the
   person was shown, not that a person typed it, and only the merge stays a separate act of the person."
6. **Held, not applied by ADR-0179 (Q-277-2): SPEC-0032 rule 1 and REQ-039 AC2.** Brief #277 answer 4 asks the router to re-run the
   head's governance run when a confirmation is posted. That needs the permission `actions: write` on the router's token, which
   rule 1 and REQ-039 AC2 exclude ("holds only the permissions pull-requests write, issues write, contents read, checks read and
   statuses read"). If the maintainers accept it, rule 1 gains: "In solo mode, on a valid confirmation, `route.py` re-runs the
   head's latest failed governance run once (`actions: write`, used for nothing else)", and REQ-039 AC2 gains `actions write` in
   its list. Until then a person re-runs the red check after a confirmation, as today.
7. **Tests (SPEC-0021 rule 9, SPEC-0032 rule 14).** `tests/kit/test_solo_mode.py`: a solo confirmation clears and approves; the
   same comment in team mode counts for nothing; an agent-app comment never counts; a confirmation naming an old head, another
   login or another shape counts for nothing; the setting and the one-person check; the final-clearance check, the spec check and
   the weekly report reading it. Their marker is `REQ-039`.

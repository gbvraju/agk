# Proposed spec amendments 97 (SPEC-0021, SPEC-0025, SPEC-0032; REQ-039)

Date: 2026-10-30 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). It is applied by
ADR-0179 (brief #277), which stays `Proposed` for the maintainers' decision, and it changes
`docs/specs/0021-when-a-fix-list-verdict-s-only-item-is-the-final-commit-and.md`,
`docs/specs/0025-a-team-can-run-independent-pull-requests-in-parallel-without.md` and
`docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md`. The number 97 was confirmed by the
verdict on f58803a (Q-277-4).

1. **SPEC-0021 rule 5, a new last paragraph: the solo confirmation.** "With `review_mode = "solo"` in `agk.toml` (the default is
   `team`) and exactly one person listed in `verdict_authors` and `spec_approvers` together, a comment by that person whose lines
   are `Confirmed: <40-hex sha>`, then `Verdict: cleared|fix list|rejected <the same sha>`, then any lines, then `Shown:` and
   exactly three lines (the summary the person was shown), and last `confirmed by <login> in a session at
   <YYYY-MM-DDTHH:MM:SSZ>`, where the login is the comment's author, counts as the verdict of its second line, with its `Final:`
   lines, for the metrics, the router and the check. The person posts it from the browser or the GitHub app; a session prints its
   text and never posts it (session rule 29). The sha must be the head when it is read: for the router the head of the pull
   request, or the parent of a head that may be its covered final commit. Any other shape, another account, a comment posted
   through an app of `agent_apps`, and every confirmation in team mode or with nobody or more than one person listed count for
   nothing."
2. **SPEC-0021 rule 6, a sentence added.** "Solo mode needs exactly one person in `verdict_authors` and `spec_approvers` together:
   `reviewers.py --check` (governance) fails naming the setting `review_mode` when nobody or more than one person is listed."
3. **SPEC-0025 rule 4, a sentence added.** "Solo mode lists one person, so a confirmation by the pull request's own author counts,
   as any verdict does with one listed author."
4. **SPEC-0032 rule 5, a new last paragraph.** "In solo mode, each line `Approve: SPEC-<n>` between the verdict line and `Shown:` of
   the one person's confirmation (SPEC-0021 rule 5) counts as `Approve: <confirmed sha> SPEC-<n>`, for the router,
   `check_specs.py` and `check_final_clearance.py`. `check_specs.py` reads the sha by the rule of a short `Approve: SPEC-<n>`
   line: it counts only when the confirmed sha is the `head_sha` of the latest `pull_request` run created before the comment
   (GitHub's times), and the spec at the head must equal the text at that sha apart from its status line. One comment is then the
   verdict, its `Final:` lines and the approval together; after it is on the pull request the session makes the status commit,
   alone, as today. In team mode such a line counts for nothing; the person still merges."
5. **SPEC-0032 rule 6, a sentence added.** "In solo mode the confirmation is the person's yes, posted from the person's own
   account. GitHub cannot tell a comment the person typed from one a session posted under the same account, so the kit cannot
   prove who typed it: session rule 29 (a session never posts a comment whose first line is `Confirmed:`) and the conductor's
   guard, which refuses such a comment by name, are what hold it."
6. **Held, not applied by ADR-0179 (Q-277-2, the verdict on f58803a): SPEC-0032 rule 1 and REQ-039 AC2.** Brief #277 answer 4 asks
   the router to re-run the head's governance run when a confirmation is posted. That needs the permission `actions: write` on
   the router's token, which rule 1 and REQ-039 AC2 exclude ("holds only the permissions pull-requests write, issues write,
   contents read, checks read and statuses read"). If the maintainers accept it, rule 1 gains: "In solo mode, on a valid
   confirmation, `route.py` re-runs the head's latest failed governance run once (`actions: write`, used for nothing else)", and
   REQ-039 AC2 gains `actions write` in its list. Until then the person re-runs governance or pushes after posting a
   confirmation, and the guide says so.
7. **Tests (SPEC-0021 rule 9, SPEC-0032 rule 14).** `tests/kit/test_solo_mode.py`: a solo confirmation clears and approves; the
   same comment in team mode counts for nothing; an agent-app comment never counts; a confirmation naming an old head, another
   login, another account or another shape counts for nothing; the setting and the one-person check; the router end to end; the
   final-clearance check; the spec check and its refusals (another account, an agent app, two people listed, another head than
   the runs show); the weekly report; the rules. `tests/kit/test_conductor_guard_confirmed.py`: the guard refuses a `Confirmed:`
   comment by name. Their marker is `REQ-039`.

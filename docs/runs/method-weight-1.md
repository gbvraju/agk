# Method weight 1 (L1): what one delivered requirement costs the maintainers today

Date: 2026-10-21 (from `date -u`). This is the baseline for the lighter-path brief (L2 to L4), judged against it in `method-weight-2.md` after the next three requirements. Every number below was read from the
GitHub REST API (GET only), from the metrics script run live (`metrics.py --today 2026-10-26`: the week 2026-W43, which is not over, so the 31 pull requests closed so far), or, for project PR #1 to #7, from
the git history of that project; the counts follow the rules below; nothing is typed in. The criterion g project is not named (ADR-0025 decision 6); its pull requests are "project PR #n".

## How things were counted

- **A requirement's pull requests:** the intake pull request (the three files), the rulings-and-approval pull request, and the build pull request. A rulings pull request that carried several requirements
  (#92 for REQ-021 and REQ-022; #102 for REQ-023, REQ-024 and REQ-025) is counted in full for each requirement in "actions (full)" and split equally in "actions (split)"; the 15 pull requests count once in the totals.
- **A maintainer action** is one comment whose first line starts with `Verdict` (a verdict, whether the maintainers posted it or the session posted it from their message), or a comment that records the
  maintainers' word or ruling that is not a verdict (first line `Rulings for`, `CI on` or `Confirmed`), or the merge. The implementation agent's own replies (first line `Reply`) are not counted (1 on #93).
  A comment was told apart as posted by the session from the footer `claude.ai/code/session` it carries.
- **Fix lists:** comments whose first line starts with `Verdict` and contains `fix list`. **Commits after the first verdict:** the commits of the pull request whose committer date is later than the first
  verdict comment. **Hours open:** created to merged, one decimal, as `hours_open_to_merge`. **Elapsed:** from the intake pull request's opening to the build's merge, waiting and the night included.
- **A final commit that only changed status lines:** the last commit of the pull request, when every line it adds or removes is a `- Status:` line, a decisions-log row or a register line (checked on the
  commit's patch). **A fix list whose only item is the final commit:** its text says `One item` and `final commit`.

## Per requirement

| Requirement | Pull requests | Number | Actions (full) | Actions (split) | Fix lists | Commits after the first verdict | Elapsed hours, intake open to build merge |
| --- | --- | --- | --- | --- | --- | --- | --- |
| REQ-021 | #84, #92 (shared), #93 | 3 | 10 | 8.5 | 2 | 3 | 22.8 |
| REQ-022 | #91, #92 (shared), #94 | 3 | 8 | 6.5 | 2 | 2 | 12.5 |
| REQ-023 | #99, #102 (shared), #103 | 3 | 9 | 6.3 | 2 | 2 | 3.6 |
| REQ-024 | #100, #102 (shared), #104 | 3 | 9 | 6.3 | 2 | 2 | 3.9 |
| REQ-025 | #101, #102 (shared), #105 | 3 | 9 | 6.3 | 2 | 2 | 8.9 |
| REQ-026 | #108, #109, #111 | 3 | 8 | 8.0 | 1 | 1 | 6.9 |

The 15 pull requests together: 42 maintainer actions (8 fix lists, 15 cleared verdicts, 4 other words, 15 merges), 28 commits, 9 commits after a first verdict.
Per requirement that is 7.0 actions on average (split shared pull requests); the full counts run from 8 to 10.

## Per pull request

| Pull request | Role | Hours open | Commits | Fix lists | Cleared | Other words | Commits after first verdict | Actions | Last commit only status lines | `review_rounds` of the metrics |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| #84 | REQ-021 intake | 2.5 | 3 | 0 | 1 | 0 | 0 | 2 | no | 0 |
| #91 | REQ-022 intake | 0.5 | 1 | 0 | 1 | 0 | 0 | 2 | no | 0 |
| #92 | REQ-021 rulings, REQ-022 rulings | 5.7 | 2 | 1 | 1 | 0 | 1 | 3 | yes | 0 |
| #93 | REQ-021 build | 3.4 | 4 | 1 | 1 | 2 | 2 | 5 | no | 0 |
| #94 | REQ-022 build | 0.8 | 2 | 1 | 1 | 0 | 1 | 3 | yes | 0 |
| #99 | REQ-023 intake | 0.6 | 1 | 0 | 1 | 0 | 0 | 2 | no | 0 |
| #100 | REQ-024 intake | 0.3 | 1 | 0 | 1 | 0 | 0 | 2 | no | 0 |
| #101 | REQ-025 intake | 0.6 | 1 | 0 | 1 | 0 | 0 | 2 | no | 0 |
| #102 | REQ-023 rulings, REQ-024 rulings, REQ-025 rulings | 0.7 | 2 | 1 | 1 | 1 | 1 | 4 | yes | 0 |
| #103 | REQ-023 build | 0.5 | 2 | 1 | 1 | 0 | 1 | 3 | yes | 0 |
| #104 | REQ-024 build | 0.6 | 2 | 1 | 1 | 0 | 1 | 3 | yes | 0 |
| #105 | REQ-025 build | 5.3 | 2 | 1 | 1 | 0 | 1 | 3 | yes | 0 |
| #108 | REQ-026 intake | 0.7 | 1 | 0 | 1 | 0 | 0 | 2 | no | 0 |
| #109 | REQ-026 rulings | 0.5 | 2 | 0 | 1 | 1 | 0 | 3 | yes | 0 |
| #111 | REQ-026 build | 3.8 | 2 | 1 | 1 | 0 | 1 | 3 | yes | 0 |

## Which round trips only changed status lines

- 8 of the 15 pull requests end with a commit that changed only status lines, decisions-log rows or register lines: #92, #94, #102, #103, #104, #105, #109, #111.
- 7 of them got that commit after a fix list whose only item was the final commit: #92, #94, #102, #103, #104, #105, #111. Each such round is a fix-list verdict, a commit, a full test run and a cleared verdict:
  the fix list and the cleared verdict are 14 of the 42 actions, and they carry no change of code or of a check.
- #109 had no fix list: its final commit followed the word given in the previous pull request's verdict box. #93 had a fix list with two items and its final commit, which also added a residual bullet, came after
  the word "Confirmed ... proven" (so it is not only status lines).

## The criterion g project, project PR #1 to #7 (git only)

The pull requests of that project are public, but this session reads it by git only (a read-only clone of the first-parent history, one squash merge per pull request). The GitHub API for its pull requests
is not enabled for this session; enabling it means attaching the repository with write credentials (`add_repo` with push access), which reading comments does not justify and which I did not request. So the table gives what git holds: when each was merged, the gap from the previous merge, what it changed, and how many
files outside configuration and tests it added under `site/` (the product code).

| Pull request | Merged (UTC, 2026-10-21) | Minutes since the previous merge | Title | Changed | Product code files |
| --- | --- | --- | --- | --- | --- |
| project PR #1 | 01:31Z | - | chore: install AGK 0.31.0 | 53 f, 6201 + | 0 |
| project PR #2 | 02:28Z | 57 | start: the vision and the project charter | 2 f, 77 +, 2 - | 0 |
| project PR #3 | 04:28Z | 119 | intake: REQ-101 the build reads each project's latest facts artifact (SPEC-0001 Draft, ADR | 3 f, 83 + | 0 |
| project PR #4 | 05:04Z | 36 | chore: upgrade agk from 0.31.0 to 0.32.0 | 4 f, 49 +, 2 - | 0 |
| project PR #5 | 05:30Z | 25 | docs: rule Q-S0001-1, -2 and -3 as read | 3 f, 10 +, 4 - | 0 |
| project PR #6 | 05:41Z | 10 | brief: the test runner and the artifact access proof (REQ-101) | 1 f, 67 + | 0 |
| project PR #7 | 08:13Z | 152 | chore: the TypeScript test runner (brief item 1) | 8 f, 1045 +, 2 - | 0 |

- The first commit is at 01:12Z; project PR #7 merged 7 h 1 min later. Seven pull requests merged, and none of them added a product code file: PR #7 added the TypeScript
  test runner, its configuration and one placeholder test under `site/`.
- **Not readable here:** when each pull request was opened, its comments and verdicts, its review rounds, its commits and the maintainers' actions. They need the API for that repository. They are not guessed.

## Findings (not fixed here)

1. **The metrics cannot see the weight.** `review_rounds` of the metrics is 0 for all 15 pull requests, while 8 of them carry a fix-list verdict. `metrics.verdicts` accepts the first line of a comment only
   when it is exactly `Verdict: fix list` (a full match). The fix lists are `Verdict: fix list <sha>` (#102 to #111) and `Verdict on #<n> (head <sha>): fix list` (#92 to #94), so none is counted; `cost_class`
   is `S` for all 31 pull requests of the week. Any rule of the lighter path that adds a verdict form (L3) has to be read by the same function or it will not be counted either.
2. **The comments undercount where a round was not posted.** #84 has three commits and one posted verdict (the cleared one): the rounds before it were given in conversation. The commits after the first
   posted verdict are low for the same reason, because the first posted verdict is often the last. The actions are a floor, and the commits per pull request (28 in 15) are the measure that does not
   depend on what was posted.
3. **The conversation is not counted.** The question rounds before the intake files are written and the boxes the maintainers paste are not pull request comments. The bodies of #99, #100, #101 and #108
   say that the questions were asked first and answered (4 rounds, 1 each); #84 and #91 do not say.
4. **Elapsed hours include waiting.** #92 was open 5.7 h; #105 was open 5.3 h; #111 was open 3.8 h; the elapsed hours per requirement (REQ-021 22.8 h, REQ-022 12.5 h, REQ-023 3.6 h, REQ-024 3.9 h, REQ-025 8.9 h, REQ-026 6.9 h) contain nights and waits for CI, not work. The pull requests that merged within an hour of opening (#91, #94, #99, #100, #101, #102, #103, #104, #108, #109) show how short a round trip is when the maintainers answer at once.

## The baseline for L2 to L4

| Measure | Now |
| --- | --- |
| Pull requests per requirement | 3 |
| Maintainer actions per requirement (shared pull requests split) | 7.0 (full counts 8 to 10) |
| Pull requests whose last commit only changed status lines | 8 of 15 |
| Fix lists whose only item was the final commit | 7 of 8 |
| Elapsed hours, intake open to build merge | 22.8, 12.5, 3.6, 3.9, 8.9, 6.9 (REQ-021 to REQ-026) |

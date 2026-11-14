# ADR-0529: The planner reads by milestone and caches

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0523, ADR-0153, SPEC-0034 rule 18, brief #1251, plan #661
- Requirements: REQ-050

## Context

On a customer project with 652 open briefs `session.py plan` took about five minutes and about 700 REST calls a pass
(brief #1251): `survey()` read every pull request ever (`pulls?state=all`), one GET for each `Depends-on`, and the
comments of every open brief one by one to find the takes, and only then applied the milestone order of ADR-0523.
The conductor plans after every merge and verdict and each builder runs `next`, so two builders and a conductor near
GitHub's 5,000 calls an hour. Build (a) of the brief (answers 1, 2, 4 and 5) changes what the plan reads; build (b)
(answers 3 and 6: the cache with conditional requests, and the conductor's change-only re-plan) is separate.

## Decision

1. Judged from the listing (answer 1). The plan reads the open briefs once, as before (one paged listing; each issue
   carries its milestone), and judges each from that listing alone where it can: stale, parked, its shape, and its
   `Depends-on`: a dependency in the open-briefs listing or among the open pull requests is open, any other is closed,
   with no GET per dependency. The open-briefs listing is read whole, not milestone by milestone, because a
   dependency, a take and the hours a brief unblocks (ADR-0523) can sit in a later milestone (Q-1251-1).
2. Comments only while slots are free (answer 1). The briefs that pass are read in the milestone order of ADR-0523
   (milestone, then the hours they unblock, priority, the smaller own hours and number); the comments of one are read
   only until the free briefs found fill the plan's free slots. The plan starts with `max_builders` briefs and, while
   a slot stays free and an unread brief is left (one was held, taken, overlapped or had no build to start), reads
   more and plans again; a read is never repeated within one run of the plan. `[plan] active_milestones` bounds the
   walk as before. The comments of a brief labelled `agk:taken` and of a brief that an open pull request names are
   always read: they are the running work.
3. The take label (answer 2). `session.py claim` adds the label `agk:taken` to the brief after its take holds (a
   failed label is reported and the take stands: the comments, not the label, decide). The label is a hint that makes
   a take visible in the listing; a stale label costs one comment read, never a wrong start. The kit has no release
   command (a `released:` is a comment a session posts) and the router and the merger are not changed (the brief's
   contexts), so nothing removes the label in this build; the label is created by GitHub on its first use and is
   listed in the setup steps of `docs/guides/getting-started.md`.
4. The pull requests (answer 4). The plan reads `pulls?state=open` and the closed ones by `sort=updated`, newest
   first, only until a page ends before its window (14 days, the merge rate's, or `claim_hours` when longer); it
   never reads `state=all`. A brief built in parts whose next build would start and that has a take reads its own
   timeline once (`issues/<n>/timeline`, the pull requests that name it) to find a build merged before the window;
   when the timeline cannot be read it reads the closed pull requests whole, once.
5. The cost is printed (answer 5). The plan ends with `reads: <n> calls (<m> from cache), <s> s` (`<m>` is 0 until
   build (b) adds the cache), `--json` carries `reads` with `calls`, `cached` and `seconds`, and the plan writes the
   same to `agk-plan-reads.json` in the checkout's git directory, which git never tracks. `checklist.py` adds
   `plan reads <n> calls (<m> from cache), <s> s` to its point 8 measure when the file is there (it sets no status),
   and the conductor's re-plan prints the `reads:` line.
6. `next`, `claim`, `demand` and `ids` read as before: they need every take (`ids` the reserved numbers) and are a
   builder's single read, not the pass that runs after every event.

## Consequences

A plan of hundreds of briefs costs a handful of calls: the listing's pages, two pull-request reads and the comments
of the briefs it starts and of the running work. The plan no longer lists, as skipped, a brief whose comments it did
not read (held, taken or a question on it), since it never looked. Session rule 18 says `claim` "posts one comment
and nothing else"; the label is not a comment, and the rule's text is left to the maintainers (Q-1251-2).
Protected path classes changed: `scripts/agk/` (`session.py`, `session_plan.py`, `checklist.py`), `.claude/`
(`.claude/agents/conductor.md`, the re-plan line), `tests/kit/` (`test_session_plan_reads.py`, new) and `agk.toml`
(the new test file added to the `[[testing.map]]` entries of `scripts/agk/session_plan.py` and `scripts/agk/session.py`).

## Residual

- 2026-11-14: Q-1251-1 (the listing read whole, not milestone by milestone) and Q-1251-2 (session rule 18's
  wording) are this session's conservative readings, for the maintainers.
- 2026-11-14: a dependency that is an open issue without the `agk-brief` label and not a pull request is read as
  closed, as answer 1 says; such a `Depends-on` is not a shape the kit files.

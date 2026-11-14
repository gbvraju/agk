# ADR-0548: The reads reuse what GitHub has not changed

- Status: Proposed
- Date: 2026-11-14
- Deciders: maintainers
- Related: ADR-0529, ADR-0523, SPEC-0030, brief #1251, plan #661
- Requirements: REQ-050

## Context

Brief #1251 found that a plan of a large project took about five minutes and about 700 REST calls a pass, and its
Correction of 2026-11-14 that every wait re-reads whole comment lists each minute: `session.py watch --pr` the pull
request and all its comments, `Told` and `watch --assign` every page of the one `agk-conductor` issue, which only
grows. Build (a) (ADR-0529) changed what the plan reads; ADR-0529 says build (b) (answers 3, 3b, 3c and 6: the cache
with conditional requests, the waits, the issue roll-over and the conductor's change-only re-plan) is separate and
records none of its choices. This ADR records them.

## Decision

1. The read cache (answer 3). Every plain GET of `session.py`, and so of every script that reads through it, is
   sent with `gh api -i` and, when the cache holds an ETag for that exact endpoint, `If-None-Match`; a `304`
   returns the kept body, which GitHub does not count against its rate limit, and is counted as `from cache` in the
   plan's `reads:` line. The cache is one JSON file per repository in a folder of the user's temp folder
   (`agk-read-cache`), never in the checkout; `AGK_READ_CACHE` names another folder, and `off` turns the cache off.
   The folder is made with mode 0700 and used only when it is a real folder that, on POSIX, the user owns and that
   its group and others cannot write; otherwise every GET is asked as before. A response without an ETag is never
   kept. Writes merge over what another run wrote meanwhile and replace the file atomically; at most 4000 entries
   per repository are kept, the most recently read.
2. The plan's `since` read (answer 3). Each plan notes its start in the cache file. The next plan makes one
   repository-wide `issues/comments?since=<that start less 120 seconds>` read; an issue's comment page that the
   cache read after that time, and that the read does not name, is answered from the cache with no request. The
   120 seconds cover a difference between the local clock and GitHub's.
3. The waits (answer 3b). A wait reads an issue's comments whole once and then only `?since=<the newest
   created_at it has seen>`, merged by id, so that a comment of the same second is never missed and an edited one
   replaces its text: `watch --pr` for the pull request and its brief, `watch --pr --session` for the
   `agk-conductor` issue (whose first read is only its last page), and `watch --assign`. Each read goes through the
   cache, the pull request's too. The pause doubles from `--interval` up to 300 seconds while a poll finds nothing
   new and returns to `--interval` on a change; a slot's `--assign` wait never sleeps past its bound.
4. The roll-over (answer 3c). `session.py rollover`, which the conductor runs at the end of each pass and its guard
   allows in exactly that form, opens a new issue with the old title and the `agk-conductor` label when the newest
   open one has more than 500 comments, posts `Continued in #<new>` on the old one and closes it. It posts nothing
   while a `Request:` there waits for its `Assign:` or a slot's lease there is live, and says `not now`. Every reader
   takes the newest open issue with the label instead of failing on two, and the waits follow a `Continued in #<n>`
   by a listed verdict author.
5. The change-only re-plan (answer 6). `session.py plan --if-changed` reads the most recently updated issue or pull
   request (`issues?state=all&sort=updated&direction=desc&per_page=1`, a 304 when nothing changed) and reuses the
   last plan, kept in the cache file, when that newest change, the checkout's commit and its `agk.toml` are the same
   and the plan is under 30 minutes old, since takes and stalls age by the clock; it then says `plan: unchanged
   since <time>` (`unchanged` in `--json`). `--record` always plans. The conductor's re-plan is
   `plan --json --if-changed`, and it reads only the plan's `Start`, `waits for` and `reads` lines;
   `skills/review-pass/SKILL.md` keeps `plan --json`, which still works (the maintainers' answer to Q-1251-3).

## Consequences

A waiting builder's quiet poll costs no counted call after each endpoint's first read, a warm plan of 600 briefs
costs one counted call in the recorded double, and an unchanged re-plan costs none. A body read through the cache can
be as old as GitHub's own ETag allows, no older. Session rule 32 says "the one open issue labelled `agk-conductor`";
after a roll-over two can be open for a moment, and the newest is the one. Protected path classes changed:
`scripts/agk/` (`session.py`, `session_plan.py`), `.claude/` (`.claude/agents/conductor.md`,
`.claude/hooks/conductor_guard.py`) and `tests/kit/` (`test_session_plan_reads.py`, and the tests of two open
`agk-conductor` issues, the usage line and the count of posts).

## Residual

- 2026-11-14: a deleted comment is not reported by a `since` read, so a cached comment page keeps it until its issue
  gets a new comment or the entry is dropped.
- 2026-11-14 (verify): `gh api -i` prints the status line and the headers before the body and, on a 304, prints them
  and exits non-zero with `HTTP 304`; the code reads the status from the output whatever the exit code, and output
  without a status line is read as a plain body.
- 2026-11-14: session rule 32's wording (the one open `agk-conductor` issue) is the maintainers' to update.

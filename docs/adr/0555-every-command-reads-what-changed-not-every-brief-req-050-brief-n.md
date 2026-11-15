# ADR-0555: Every command reads what changed, not every brief

- Status: Accepted
- Date: 2026-11-15
- Deciders: maintainers
- Related: ADR-0553, ADR-0548, ADR-0529, brief #1314, brief #1309, brief #1251, plan #661
- Requirements: REQ-050

## Context

Brief #1314 found, by an audit of the GitHub reads inside loops in `scripts/agk/` on a project with about 650 open
`agk-brief` issues, that `conductor.py watch` read every page of the comments of every open brief and pull request
on each poll (about 650 calls a minute while it waits), and that a contended `session.py claim` read them all again
(`stale_view`, then the overlap survey). CI, local and personal mode run the same scripts. This ADR covers build (a):
the shared reader, `conductor.py watch`, `session.py claim` and the setting; build (b) switches the other loops.

## Decision

1. One shared helper, `session.changed_comments(repo, since)`, makes the repository-wide read of the comments
   created or edited since a stamp: `issues/comments?since=<stamp less 120 s>&sort=updated&direction=asc`, every
   page before any line is judged, each comment once (its copy with the newest `updated_at`, by id). Comments on
   pull requests are issue comments and are included. A page that cannot be read, or a comment that names no id or
   no issue, makes the helper return nothing usable, and the caller reads as before (rule 5). The plan's
   `changed_since_pass` (ADR-0548) uses the same helper.
2. `conductor.py watch` reads the two listings (open briefs, open pull requests) and that one delta since the watch's
   `since`, then judges, for each listed issue, the delta's comments exactly as it judged the full pages: a comment
   created after `since` whose first line wakes. The lines are those of a read of every page, for the same GitHub
   state, since a comment created after `since` was also updated after it. A quiet poll is three requests that the
   read cache answers with `304` (not counted by GitHub).
3. `session.py claim` keeps a comment store beside the read cache (`<owner>__<name>.comments.json` in the user's
   temp folder, never the checkout, written whole by write and rename): for each open brief, the full list of its
   comments and the stamp of the run that last made it current. A run reads the delta since that stamp and merges it
   by id (an edited comment replaces its stored copy). A brief's comments are then answered from the store only when
   the open-brief listing of this run shows its `comments` count, and that count is 0 or equals the stored list's
   length; otherwise (first run, a cleared or corrupt or old-schema store, a deleted comment that lowers the count, a
   comment newer than the delta that raises it) the brief is read from GitHub as before and stored. A comment that
   the run posts drops the brief from the store, so the read after a take always asks GitHub. Two processes on one
   machine each keep their own store in the run and write it whole; a lost write costs calls, never an answer.
4. A setting `github_reads` of the `[flow]` table of `agk.toml` takes `"delta"` (the default) or `"full"` (the
   per-item reads of before this ADR, with no delta and no store), kept for one release. Another value is refused
   naming the setting. `conductor.py watch` prints `reads: delta` or `reads: full` once, on standard error, so that
   its standard output stays the same in both modes.
5. A test file, `tests/kit/test_github_read_budget.py`, with a recorded 650-brief fixture
   (`tests/kit/fixtures/read_budget_650.json`, invented data), proves that each switched command prints the same
   output in both modes, through edits, deletions and new comments, and holds a budget of counted calls (all but the
   `304`s) on a warm run: `conductor.py watch --once` with nothing new at most 3, with one new `Report:` at most 4;
   `session.py claim` at most 8; `session.py review-queue --fingerprint` at most 6; `session.py plan` at most 35. A
   broken budget fails naming the command, the budget and the count.

## Consequences

A conductor waiting on a 650-brief project makes three requests a poll, answered by `304` when nothing changed,
instead of about 650; a contended claim reads only the briefs whose comments changed. A project returns to the old
reads with one line, `github_reads = "full"`. Protected path classes changed: `scripts/agk/` (`session.py`,
`conductor.py`), `tests/kit/` (`test_github_read_budget.py`, `fixtures/read_budget_650.json`) and `agk.toml` (the
new test file in the `[[testing.map]]` entries of `session.py` and `conductor.py`, so that a change to either selects
it).

## Residual

- 2026-11-15 (verify): GitHub's `since` filter of `issues/comments` compares `updated_at`, which an edit changes;
  that is GitHub's documented behaviour and was not measured here.
- 2026-11-15: a comment edited while the delta is being paged moves to the end of the `updated` order and can shift
  one other comment across a page boundary. The watch reads the same delta again on its next poll; the claim store
  catches a missed new comment by its count, not a missed edit, which the next claim's delta reads again only while
  it is newer than the stamp less 120 s.
- 2026-11-15: build (b) of brief #1314 switches `stalls.py`, the per-pull-request loops of `conductor.py`, `caps.py`
  and `session_plan.py`, and holds the rest of the budget table.

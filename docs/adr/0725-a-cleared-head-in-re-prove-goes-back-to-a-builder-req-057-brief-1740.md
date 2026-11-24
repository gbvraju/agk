# ADR-0725: A cleared head in re-prove goes back to a builder

- Status: Accepted
- Date: 2026-11-22
- Deciders: maintainers
- Related: brief #1740, brief #1735, brief #1733, brief #1071, brief #1358, ADR-0385, ADR-0453, ADR-0570, ADR-0722
- Requirements: REQ-057, REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude/`, `config/`, `agk.toml`

## Context

On 2026-11-22 #1723 was cleared at 16:03 IST, before #1719 merged; both change `.claude/agents/steward.md`. The
merger held it as `re-prove (rule 6 of SPEC-0050)` from 16:46, but the router kept `agk:merge-ready`, the
conductor's merge queue named the owner's `--owner` command, the plan counted it "safe to merge", and no builder was
started: `route.state` never read the default branch's changes, and a cleared label is not a builder state, so a
hand-over never became `agk:handover`.

## Decision

1. ADR-0385's states gain `agk:reprove` (actor `builder`, "merge the default branch and re-prove"). For a pull
   request whose state would be `agk:merge-ready` or `agk:owner-merge`, the router reads one
   `GET compare/<head>...<default branch>`. Its re-prove files are the pull request's changed files, renames from or
   to included, that the compare's files also change (SPEC-0050 rule 6, no exemption). With any, and the merge not
   `dirty` (a conflict stays `agk:conflict`), the state is `agk:reprove`; when every one is a shared index of
   `[flow] shared_indexes` it is `agk:review` instead, the conductor's light re-prove (amendment 171). With
   `[flow] max_behind_merges` set and the compare's `ahead_by` (the default branch's commits past the merge base)
   above it, the state is `agk:reprove` too. A compare that cannot be read leaves the state as it was and prints
   `re-prove: #<n> unknown (cannot be read)`.
2. Every state before `agk:merge-ready` and `agk:owner-merge` in the order wins over `agk:reprove`.
   `agk:reprove` joins amendment 162's builder states, so a builder's hand-over makes it `agk:handover`.
3. `conductor.py sweep`'s `HANDOVER #<pr> <minutes>m` line ends ` re-prove <file> #<m>` when a full `re-prove:`
   line names the pull request. `.claude/agents/conductor.md` restarts such a hand-over with the step "merge the
   default branch and re-prove"; `kit/templates/runtime/builder.txt` tells a watching builder what to do on
   `agk:reprove`.
4. No owner merge is asked while a re-prove is due: `conductor.merge_queue`'s `not queued:` line for an owner-only
   hold reads the re-prove state with local git first and prints `re-prove (rule 6 of SPEC-0050)` without the owner
   command; `route.owner_ask`'s `agk:owner-merge` becomes `agk:reprove`; `session.open_owner_items` drops the
   owner-merge item of a pull request labelled `agk:reprove`; the conductor posts an owner-merge `Owner needed:` only
   after a `would-be merge: pass` on the current default branch.
5. Every reader of the state labels lists `agk:reprove`; `session_plan.READY_LABELS` does not, so the plan no longer
   counts it as ready.

## Consequences

A cleared head that a newer merge puts in re-prove goes back to a builder on the next push to the default branch,
with no session needed to notice it, and the owner is never sent to a held merge. One more GET per cleared pull
request at each routing.

## Residual

- 2026-11-22: the router's behind count is the compare's commit count, not `merge_cleared.py`'s first-parent count;
  the two agree on a squash-only default branch (brief #1740 Q-2).

# ADR-0273: merge_cleared.py runs governance after the merge, stops on red and records each merge (REQ-046, brief 551)

- Status: Proposed
- Date: 2026-11-04
- Deciders: maintainers
- Related: ADR-0261, ADR-0263, ADR-0265, SPEC-0039, SPEC-0032
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

SPEC-0039 (Approved on #519, ADR-0261) splits the guarded merge into the builds of its rule 12.
Build (a) (ADR-0263) read the setting and the verdict; build (b) (#533, ADR-0265) added the
re-checks, the hold list and the pinned merge, and ran nothing after it. This is build (c): the
rest of rule 6 (the governance run after the merge, the red-branch stop) and rule 7 (the record
line). The ADR number was reserved for brief #551 by the conductor (the field note on #551).

## Decision

1. **The record issue, before the merge (rule 7).** After the red-branch check, the command picks
   the issue its record line goes to: the one open local-mode record issue (title starting
   `Local mode since`) while one is open, otherwise the one open issue labelled `agk-auto-merge`.
   With neither, or with more than one of the kind it would use, it merges nothing and prints
   `held: no record issue (rule 7)` (exit 3).
2. **The record line, right after the merge (rule 7).** The first thing after a merge is one
   comment on that issue, `Auto merge: #<n> <merge sha> <UTC time> <verdict link>`, the time from
   the clock in UTC (`YYYY-MM-DDTHH:MM:SSZ`) and the link the verdict comment's `html_url` (else
   the pull request's comment anchor). It is posted before governance runs, so a merge that turns
   the branch red is still recorded. A record line GitHub does not accept leaves the merge in
   place, prints `merged <merge sha12>: the record line cannot be posted (rule 7)` and exits 1
   (unless governance is then red, below). The command writes no file.
3. **The governance run (rule 6).** Still holding the `merge-cleared` lock, the command runs
   `git fetch origin <default branch>`, resolves the merge commit and its first parent, adds a
   detached worktree of the merge commit in a new temporary folder outside the checkout, and runs,
   as one argument list with no shell, `<this Python> scripts/agk/lock.py run --name heavy
   --session merge-cleared -- env -i PATH=<PATH> HOME=<a scratch folder> make -C <worktree>
   governance AGK_BASE=<parent of the merge commit>`, where `lock.py` is the file beside
   `merge_cleared.py` (the project's own). `env -i` leaves only `PATH` and `HOME`, so no token
   reaches the merged code. Its output goes to standard error, so standard output keeps its one
   line. The worktree is removed (`git worktree remove --force`, then the folder, then
   `git worktree prune`) in every case, also when a step fails.
4. **The red-branch stop (rule 6).** A fetch that fails or does not bring the merge commit, a
   worktree that cannot be added, or a governance run that exits non-zero counts as red, with the
   failing step named (`fetch`, `worktree` or `make governance`): a run that cannot show the
   branch green stops merging, the safe side. The command then reads the open `agk-brief` issues,
   keeps the router's own (`session.is_red`), and opens or updates the red-branch issue through
   `route.write_red`, with `route.red_body(<the step>, <merge sha>, <the merge commit's URL>)`, so
   the title, the label and `Priority: 0` are the router's and no cause is named. It prints
   `merge-cleared: stopped: default branch red after #<n>` and exits 1 (rule 6). When the issue
   cannot be written, the line adds `(the red-branch issue cannot be written)`. It never reverts.
5. **`route.py`.** The tail of `route_branch` that opens or updates the red-branch issue is moved,
   unchanged, into `write_red(repo, open_red, body, labels)`, which `route_branch` calls; the
   router's behaviour does not change.
6. **The two meet (brief answer 2).** The open issue titled `The default branch is red`, whoever
   wrote it, holds every later run (build b's `held: the default branch is red (rule 5)`); the
   `merge-cleared` lock makes a second run wait until the first run's governance and issue are
   done.
7. The build (b) test fixtures change only where build (c) needs them: the saved world holds one
   open `agk-auto-merge` issue, the fake `gh` answers the writes of this build, a fake `make`
   records its argument list and environment, the remote is a local bare repository whose path
   ends `github.com/<owner>/<repo>.git` (so nothing reaches the network) holding a fixed merge
   commit, and the text check that `"make"` never appears now allows it only in the governance
   run.

## Consequences

With `auto_merge` off, the default, nothing changes. With it on, every merge is recorded on the
record issue and followed by governance on the merged default branch; a red run opens the
red-branch brief and holds every later merge until it is closed. `kit/manifest.json` and
`kit/hashes.json` are unchanged: no new file is installed.

## Residual

- 2026-11-04: the red-branch issue the command opens is written under the conductor's login, so
  the router's `is_red` (which trusts only its own token) neither updates nor closes it; the
  command's hold reads the title alone, so it holds until a person closes it (Q-551-2, due
  2026-12-31).
- 2026-11-04: on Windows the run needs `env` and `make` on `PATH` (Git for Windows and a `make`
  port) `(verify)`; without them the run fails and counts as red, the safe side (Q-551-3, due
  2026-12-31).

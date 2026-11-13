# ADR-0329: The conductor's merge queue merges in batches and waits once (REQ-037, brief 643)

- Status: Accepted
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0308, ADR-0297, ADR-0302, ADR-0265, SPEC-0039
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `.claude/`, `agk.toml`

## Context

ADR-0308 decision 6 reserved build (b) of brief #643, `conductor.py merge-queue`, as a loop over
`merge_cleared.py` that stops at the first `held` or `stopped` line. The conductor's field note of
2026-11-07 on the brief, from the owner's question about the lost speed, changes that decision: the
conductor's own merge scripts waited for the default branch's run after every merge, which threw
away the batched main checks of ADR-0302 (about 20 minutes a merge). Row 3 of the conductor catch
log (a merge result not read in full) and row 22 (one page of check runs read as all of them) are
the incidents this command guards. The ADR number was reserved by the field note.

## Decision

1. **The command.** `python3 scripts/agk/conductor.py merge-queue [--dry-run] [--max-batch N]`,
   installed with the kit. It reads the default branch's settings as `merge_cleared.py` does
   (`merge_cleared.ruled`: `auto_merge` on, not `paused`, the reviewers, the required checks); with
   auto-merge off it is refused naming the setting, the dry run too. Every open pull request that is
   not a draft is read once more before its holds (decision 5), then judged by `merge_cleared.holds`,
   the one reading of SPEC-0039 rules 3 to 5 and 7 that merges nothing, which `merge_cleared.py`
   itself runs before its check and its merge. A pull request whose latest verdict does not clear
   its head is left out silently; one that is cleared and held is printed as `not queued: #<n>
   <sha12>: <reason>`. The clearing verdict's author must also be a listed verdict author
   (`verdict_authors` of the default branch's `config/reviewers.yaml`, counted as `session.py`
   counts them), the brief's "by a listed author"; otherwise the line names that setting.
2. **The order and the batch.** The queued pull requests are merged in the order of their clearing
   verdicts (creation time, then comment id), at most `--max-batch N` of them (5 by default; the
   rest are counted as `<k> more wait for the next batch`), each through its own process
   `python3 scripts/agk/merge_cleared.py --pr <n> --sha <head>`, the project's own file beside
   `conductor.py`, whose one line is printed in full. Its check before the merge against the latest
   default branch (ADR-0297, SPEC-0039 rule 6) and its governance run after the merge stay as they
   are; nothing waits for the default branch's CI run between two merges.
3. **The stop.** The queue stops at the first run that does not exit 0 (a `held`, a `refused`, a
   `stopped` or an unreadable line: row 3, the red line is read) and prints `merge-queue: stopped at
   #<n> (exit <code>); merged: #a #b` or `merged: none`; nothing after it runs. A run whose line
   says `merged` counts for the batch whatever its exit (a record line that could not be posted
   still merged); a `merge-cleared: stopped:` line (the default branch red after its own governance
   run, the red-branch issue filed) counts too and ends the queue with no further wait.
4. **One wait at the end.** When at least one pull request merged and no `stopped:` line ended the
   queue, the command waits once for the default branch's run on the last merge commit (the pull
   request's merge sha from `merge_cleared.py`'s line, made full with local git after its fetch):
   it fetches the default branch and reads the last 100 push runs of `governance.yml`, judged by
   `full_run.covered` (ADR-0302: a run replaced while it waited is covered by the next completed run
   that contains the commit), every `conductor_poll_seconds` (60 by default), for at most
   `merge_queue_wait_minutes` of the `[flow]` table (60 by default; this repository sets neither).
   Green prints `merge-queue: <branch> green at <sha12> after the batch #a #b` and exits with the
   stop's code (0 when nothing stopped); red prints `merge-queue: stopped: <branch> red at <sha12>
   after the batch #a #b` and exits 1; a run not ended in time is said as such, exit 3 unless a stop
   already set the code. A read of the runs that fails is printed and tried again, never read as a
   state. In local mode (`execution = "local"`, or the open local-mode record issue:
   `merge_cleared.local_mode`) there is no run to wait for, and the command says so.
5. **Settling.** After a push to the default branch GitHub works out each open pull request's
   mergeable state anew, and until it has, a read says `unknown`, which SPEC-0039 rule 5 holds as a
   conflict. Before the holds of each open pull request that is not a draft, and before each merge
   after the first of a batch, the queue reads the pull request again, at most 10 times 3 seconds
   apart, until the state is known; what it says then is `merge_cleared.py`'s to judge
   `(verify: GitHub's documentation says the value is computed in the background after a read)`.
6. **What it never does.** It posts no comment, no verdict and no approval, pushes nothing, turns
   GitHub's auto-merge neither on nor off, and merges only through `merge_cleared.py`, so principle
   2 and session rule 2 hold as written. `--dry-run` prints the order and merges nothing.
7. **`merge_cleared.py`.** Its run is unchanged in behaviour: the settings and the holds it ran
   inline are the functions `ruled`, `holds` (raising `NotCleared`, a `Held`, when the verdict does
   not clear the head) and `local_mode`, so that the queue reuses them and copies no rule.
8. **The guard and the builders.** `.claude/hooks/conductor_guard.py` allows exactly
   `python3 scripts/agk/conductor.py merge-queue`, with `--dry-run`, then `--max-batch <1 to 99>`,
   or both in that order, the project's own regular file: the dry run always, a run that merges only
   when `[flow] auto_merge` reads on both in the checkout and at `origin/<default branch>` as last
   fetched, as `merge_cleared.py` is allowed; the hook prints the same explicit `allow` decision.
   `.claude/settings.json`'s `ask` list gains `Bash(*conductor.py*merge-queue*)`, so a builder is
   asked first, as for `merge_cleared.py` (Q-S0039-15); no `deny` and no `allow` entry is added.
9. **The lessons.** The rule line of row 3 in `.claude/agents/conductor.md` names the command within
   its word budget; the catch log's Guard column of row 3 gains `check scripts/agk/conductor.py`
   first, and row 22's `pending #643` becomes that check (`merge_cleared.py` reads every page of the
   check runs). The reference guide's "Conductor routines" section describes the command.

## Consequences

Five cleared pull requests merge in the time of one default-branch run plus five pre-merge checks,
instead of five runs; the batched main checks of ADR-0302 cover the batch, and a red run after it
names the batch. A `held` in the middle of a batch (most often the pre-merge check against a default
branch that the earlier merges moved) stops the rest until the next run of the command, which is the
conservative reading of the brief. The queue costs one GET per open pull request (plus the holds'
reads for a cleared one) and one GET of the runs per poll at the end.

## Residual

- 2026-11-06: Q-643-2, whether a `held` in the middle of a batch should skip to the next pull
  request instead of stopping; read as stopping, the brief's words.
- 2026-11-06: Q-643-3, whether the command should go on with the next batch after a green run;
  read as one batch per run, with the count of what waits, so that nothing runs on a timer
  (SPEC-0039 rule 9), and the conductor or the hourly run starts it again.
- 2026-11-06: Q-643-4, what the wait at the end means in local mode, where no run of the default
  branch exists; read as no wait, said in one line.
- 2026-11-06: the settling of decision 5 rests on GitHub's documented behaviour `(verify)`; a
  pull request whose state stays `unknown` after the reads is held by `merge_cleared.py` as today.

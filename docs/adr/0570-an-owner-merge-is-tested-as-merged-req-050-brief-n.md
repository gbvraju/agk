# ADR-0570: An owner merge is tested as merged

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers
- Related: brief #1358, alarms #1338, #1344 and #1350, ADR-0297, ADR-0417, SPEC-0039 rule 5, SPEC-0050 rule 6, plan #661
- Requirements: REQ-050

## Context

The default branch went red three times on the evening of 2026-11-15, each time after the owner merged a pull request
with the GitHub button (#1326, #1334, #1332). The guarded merge had held each one as `held: protected class` (SPEC-0039
rule 5). `merge_cleared.py` raises that hold before it builds the would-be merge and runs governance on it (ADR-0297), so
a protected pull request never got that check. The re-prove hold (SPEC-0050 rule 6) misses a new script whose test reads
every script, because the two are different files. GitHub offers its merge queue only to repositories owned by an
organization. This repository is owned by a user account, so the owner's hand merge is the only path for a protected
change.

## Decision

1. A pull request held only for an owner-only hold (a release or a protected class) still gets the check before the
   merge: the same would-be merge and governance run, then the pre-merge tests. The hold line ends
   `; would-be merge: pass` or `; would-be merge: fail`. Nothing is merged or posted. When another hold stands as well,
   the line is the same as before and no run is made. A hold that the check raises itself (a conflict, re-prove, behind)
   is reported as that hold.
2. `python3 scripts/agk/merge_cleared.py --pr <n> --owner` is the owner's merge, in every mode. It reads the pull
   request's current head and runs the same checks, with the owner-only holds lifted for that one call. It merges, pinned
   to that head, as the signed-in `gh` account (never with `AGK_MERGE_TOKEN`), and only when the would-be merge passes.
   Otherwise it refuses with the hold's line. It refuses an account that is not in `spec_approvers`, naming the setting
   and never the login. It never joins the merge queue.
3. With the merge queue on (an organization-owned repository), the owner's button queues the pull request and the
   `merge_group` runs test the combined result, so `--owner` is optional there. With the queue off, or in a user-owned
   repository, `--owner` is the way. In CI mode, `doctor.py` prints `merge queue: unavailable (user-owned repository)`
   when the queue is off in a repository GitHub reports as owned by a user. The conductor's `not queued:` line for an
   owner-only hold, and its `Owner needed:` text, name the command. The kit changes no ruleset and no workflow.
4. The result of the would-be merge is kept once per head, in `agk-would-be-merge.json` in the checkout's git folder,
   never the work tree. It is keyed by the head, the default branch's commit, the body and the run's settings, and it is
   reused while none of them changes. The file keeps the newest 50 results. Only a pass, a failed governance run and a
   failed pre-merge test are kept. A run that did not finish, or whose setup failed, runs again. This applies to the
   owner-only path and to `--owner`. A pull request with no owner-only hold is merged exactly as before.

## Consequences

The owner's merge of a protected change is tested as merged. A red result reaches the conductor before the owner's tap,
and the conductor asks the builder to update the branch. Each guarded pass on a held protected pull request runs one
governance run per head and default branch, under the heavy lock. Protected path classes changed: `scripts/agk/`
(`merge_cleared.py`, `conductor.py`, `doctor.py`), `.claude/` (`.claude/agents/conductor.md`), `tests/kit/`
(`test_merge_cleared_owner.py`) and `agk.toml` (the new test in the `[[testing.map]]` entry of `merge_cleared.py`), with
one `changelog.d/` fragment.

## Residual

- 2026-11-16: `--owner` still needs `[flow] auto_merge = true` on the default branch, as the guarded merge does
  (`Q-1358-1`). A project with auto-merge off has no guarded merge and gets no `--owner`.
- 2026-11-16: the GitHub button stays available. Nothing stops a hand merge that skips `--owner`; the ruleset is the
  owner's to set.

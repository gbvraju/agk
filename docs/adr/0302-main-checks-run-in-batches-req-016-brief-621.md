# ADR-0302: Main checks run in batches: a running check finishes, waiting ones collapse to the newest commit (REQ-016, brief 621)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0162
- Requirements: REQ-016

Protected classes: `.github/`, `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

Brief #216 put every push to the default branch in its own concurrency group of `governance.yml`
(`governance-<sha>-code`) and never cancelled one. N merges in a row therefore start N full runs of about 16 minutes
each, and every one but the last checks a version that is already out of date. The owner said yes on 2026-11-06 (quoted
in brief #621) to batching main checks to save time and GitHub Actions minutes, asking what happens to a run that is
80% done. This changes the decision of brief #216 for pushes to the default branch only.

## Decision

1. Every push to the default branch shares one fixed concurrency group of `governance.yml`
   (`governance-<default branch>-code`) with `cancel-in-progress: false`. GitHub keeps one running and at most one
   waiting run per group and replaces an older waiting run with the newer one. A running run is never cancelled, so a
   run 80% done finishes and a stream of merges never leaves the default branch unchecked. Pull request and `edited`
   groups, and their cancelling, are unchanged.
2. A default-branch commit whose own run was cancelled while it waited, or that has no run of its own, is covered by the
   next completed `governance full` push run on a later default-branch commit that contains it
   (`git merge-base --is-ancestor`); that run's result is its result. It is never green while no such run has
   completed, and a cancelled run never counts as green on its own. The rule is one function, `full_run.covered`,
   which takes the runs and a containment test, and `full_run.contained_in(root)` answers containment with git; a
   commit that git does not know is not contained (fail closed).
3. The readers of a default-branch commit's result: the backstop-escape line of `metrics.py` reads a merge commit's own
   push runs, ignores a cancelled one, and with none left reads the default branch's last 100 push runs of
   `governance.yml` through `full_run.covered` (pending is `unknown`). The router's red-branch brief (`route.py`) and
   the local-mode catch-up (`local_mode.py`) read only the tip of the default branch, whose run is never replaced
   (only a newer push replaces a waiting run); a tip whose run still waits has no check yet and is pending, and a
   cancelled one counts as failed, so neither changes. `merge_cleared.py` runs governance itself on the merge commit,
   `check_release.py`, `agk-tag.yml` and the drift audit read no CI result, and they do not change.

## Consequences

Of four quick merges, two full runs start instead of four, and nothing already paid for is thrown away. The result of
a merge whose own run was replaced arrives with the next run, up to one run later than before.

## Residual

- The metrics reader looks for a covering run among the last 100 push runs of `governance.yml`; an older merge whose
  covering run is outside them reads `unknown` (2026-11-06).

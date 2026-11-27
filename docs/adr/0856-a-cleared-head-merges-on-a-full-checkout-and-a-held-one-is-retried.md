# ADR-0856: A cleared head merges on a full checkout, and a held one is retried

- Status: Proposed
- Date: 2026-11-27
- Deciders: maintainers (the owner's yes on brief #2058, 2026-11-27T19:12:33Z)
- Related: ADR-0570, ADR-0554, ADR-0585, ADR-0593, ADR-0684, SPEC-0039, brief #2058, brief #610, brief #1358, brief #1615, plan #661
- Requirements: REQ-046

Protected classes: `scripts/agk/`, `.claude/`, `tests/kit/`, `agk.toml`

## Context

#2036 was cleared at 08:51Z and merged at 10:34Z (103 minutes). The conductor's `merge_cleared.py` ran on a shallow
clone, where `kit_hashes.problems` refuses (`the repository is a shallow clone`), so the pre-merge tests of the would-be
merge failed and the run held. `merge_cleared` never read the clone's depth, the kept result of brief #1358 (ADR-0570
decision 4) replayed that hold after the clone was made full, and the supervisor's pass started no job for a held
`cleared, not merged` head, because it changes neither the queue's fingerprint, the plan nor the sweep. The merge came
from the lapse path (ADR-0684).

## Decision

1. **A full checkout first.** `merge_cleared.full_history(root)` is the first step of `fetched_base`, the one fetch that
   the would-be merge and the kept result read: on `true` from `git rev-parse --is-shallow-repository` it runs
   `git fetch -q --unshallow origin` once and reads the flag again; a checkout that stays shallow, or a fetch that
   fails, holds with `held: the checkout is a shallow clone (setting: git fetch --unshallow)`, exit 3, before any
   would-be merge, kept result, pre-merge test or GitHub write. A full checkout, a partial clone that is not shallow
   and the merger's `fetch-depth: 0` checkout run nothing more; a folder git cannot read fails at the fetch as today.
   The status reading (`verdict_state`) and the merge queue's re-prove reading (`conductor.reprove_hold`) give that
   line as their reason instead of raising.
2. **No replay of a shallow run.** `checked_key` adds the fixed field `{"history": "full"}`, so no result kept before
   this decision is read again, and every result kept after it comes from a full checkout.
3. **The pass retries a cleared head.** After `pass_facts`, `conductor.cleared_due` reads `session.review_queue --all`
   once and the default branch's commit with one GET; a `#<n> <head7> cleared, not merged` line whose head and
   default-branch commit differ from what the pass state kept for `n` adds `a cleared head is not merged` to the
   reasons, so a conductor job starts. The state keeps the pairs only when a job starts, so a held head is retried once
   per new head or default-branch commit, never on every pass. A queue or commit that cannot be read adds nothing.
4. **The retry in the same session.** `.claude/agents/conductor.md` says that after a `held:` line whose cause is the
   checkout or a step put right since, the conductor runs the same command once more in the same session: one retry,
   not a loop. The guard (`conductor_guard.merge_allowed`) and `.claude/settings.json` are unchanged.
5. **Settings.** No new key. `ruled` still refuses or holds `auto_merge`, `auto_merge_method`, `paused`, `execution`,
   `after_merge_timeout` and `max_behind_merges` before any fetch; `merge_queue` reaches the same check through
   `run_merge`; `forge = "files"` is refused as today.
6. **Wiring.** The `[testing]` map of `merge_cleared.py` names `tests/kit/test_merge_cleared_shallow.py`; that of
   `conductor.py` names it and `tests/kit/test_watchdog_cleared_retry.py`.

## Consequences

A cleared head on a shallow conductor checkout merges on its first run, or holds naming the fix; a hold always names a
real failure of the full history. The cost is one fetch of the missing history per clone and at most one more
conductor job per held head and default-branch commit. Which of the guard or a settings `ask` entry refused the
conductor's second run on 2026-11-27 is not measured here (`Q-2058-1`); the usage line is a separate brief (`Q-MS-3`).

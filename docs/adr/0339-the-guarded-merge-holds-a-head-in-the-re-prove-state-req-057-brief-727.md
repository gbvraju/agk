# ADR-0339: The guarded merge holds a head in the re-prove state (REQ-057, brief 727)

- Status: Proposed
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0325, ADR-0297, ADR-0320, SPEC-0050, SPEC-0039
- Requirements: REQ-057

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

SPEC-0050 (Approved) rules 6 and 8 say that a pull request whose changed files the default branch
also changed after its merge base is in the re-prove state, and that `merge_cleared.py` holds it.
Its build (b) is brief #727. The requirement's ADR, ADR-0325, is still `Proposed`, so this build
cannot use a `Covered-by:` line (session rule 36) and writes its own ADR with the number the brief
reserved. The build changes the behaviour SPEC-0039 rule 6 and ADR-0297 state for the check before
the merge: it adds two holds to it, proposed in `docs/runs/proposed-spec-amendments-137.md` with the
number the conductor reserved for brief #727 (answer to Q-727-1).

## Decision

1. **The re-prove files.** `session_plan.reprove_files(root, default, head)` names, with local
   `git` only, the files changed by the head since its merge base with the default branch and by
   the default branch after that merge base, sorted. `--no-renames` names a rename by both paths,
   so added, modified, removed and renamed files all count, with no exemption (Q-S0050-7). A read
   that fails gives None, never a clean empty list. `session_plan.behind_merges` counts the
   first-parent commits of the default branch after the merge base.
2. **The holds.** `merge_cleared.py` checks them after every hold it has today and before the
   governance run of the check before the merge. It checks them once the would-be merge is built,
   so a fetch that fails and a conflict hold exactly as before and no fetch is added. The lines are
   `held: re-prove (rule 6 of SPEC-0050)`, `held: behind the default branch (setting
   flow.max_behind_merges)` and, for a read that fails, `held: re-prove (unknown)`. Each exits 3 and
   nothing is merged, recorded or filed. No line names a file, a count or a sha (principle 8).
3. **The setting.** `[flow] max_behind_merges` is optional and opt-in. When it is absent there is
   no behind hold. When it is set it is an integer of at least 0, and a head more first-parent
   commits behind than that holds. Any other value is refused before any GitHub read, naming the
   setting. This repository does not set it (Q-S0050-8).

## Consequences

A pull request that is green alone but whose files a merged change also touched is held until its
builder merges the default branch and re-proves it. The merge queue's own holds are unchanged; the
sweep lines are build (d). Nothing changes for a project with `auto_merge` off.

## Residual

- 2026-11-08: `conductor.py merge-queue` does not yet show the re-prove hold; it reads the holds
  that read GitHub (`holds`), and this one reads git (due 2026-12-31).

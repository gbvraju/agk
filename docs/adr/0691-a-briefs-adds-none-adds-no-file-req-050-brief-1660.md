# ADR-0691: A brief's `Adds: none` adds no file, and a clashed brief is skipped naming its clash

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: brief #1660, ADR-0598 (brief #1425), briefs #1648 to #1651
- Requirements: REQ-050

## Context

Briefs #1648 to #1651 each carried `Adds: none`. `session.line_entries` returned every comma entry as a path, so
`plan_names.adds_of` read `none` as a new file: `session.py plan` printed five `CLASH: ... both add none` lines and
skipped all four with the fallback reason `every build is taken or in progress`, and `check_brief.py` refused #1650
with `Adds entry none is held by #1651`. One brief alone passes, so the clash needs two open briefs. The tests were
written first (`tests/kit/test_plan_names.py`: 20 failed, 25 passed on the unchanged tree).

## Decision

1. **`none` alone is no entry** (`scripts/agk/session.py`, `line_entries`). A line whose only entry is `none`, in any
   case, gives no entry, for `Adds:` and `Touches:` alike; every reader of the lines (`adds_of`, `touches_only`,
   `touches_of`, `touch_problems`, the plan and `check_brief.py`) reads it so.
2. **`none` mixed or punctuated is refused** (`brief_problems`, new `none_problems`). `none` beside a path, or with
   punctuation such as `None.`, is refused naming the line (`rule 4` for `Adds:`, `rule 2` for `Touches:`), never read
   as a path. `Adds:` with nothing after it stays refused as today.
3. **A clashed brief names its clash** (`scripts/agk/session_plan.py`, new `clash_skips`). A ready brief that a clash
   holds (not the taken one) is listed in `skipped` with its `CLASH:` line, never with the fallback reason of
   `unplaced`.
4. **No setting reads the line.** `review_mode`, `pr_mode`, `execution` and personal mode (the sidecar's saved briefs
   are read by the same function) read it the same.

Protected path classes changed: `scripts/agk/` (`session.py`, `session_plan.py`, `check_brief.py`), `tests/kit/`
(`test_plan_names.py`) and `agk.toml` (one test-map line: `test_plan_names.py` now imports `session_plan`);
`kit/hashes.json` is unchanged (`kit_hashes.py`: ok).

## Consequences

Briefs that add no file start together; a plan that holds a brief for a clash says which clash.

## Residual

- 2026-11-21: none.

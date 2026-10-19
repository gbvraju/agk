# ADR-0044: the report's At-risk line for a pull request merged before its head was cleared (SPEC-0013 rule 18), kit 0.24.0

- Status: Proposed
- Date: 2026-10-19
- Deciders: maintainers
- Related: ADR-0021, ADR-0042
- Requirements: REQ-020

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`

## Context

G5, ruled on 2026-10-19 as a small pull request right after G4. SPEC-0013 rule 18 says the metrics field `merged_head_cleared` is the deterministic check and the
weekly product report lists such pull requests under "At risk" (amendment 15 item 3). It reports after the fact and blocks nothing; no drift finding is added.

## Decision

1. **`product_report.py` At risk gains a fifth item (v)**, after the drift line (SPEC-0011 rule 10 keeps its order (i) to (iv)): for each pull request merged in the report's
   week, `PR #N was merged before its last commit was cleared` when its last `cleared` verdict does not name the merged `head` (the verdict's sha is a prefix of the head,
   compared case-insensitively; a `cleared` verdict with no sha, or only `fix` or `rejected` verdicts, does not clear it), and `PR #N was merged with no verdict` when it has
   no verdict at all. Lines are in pull request order and end with the pull request link like every line. Derived from `pull_requests[].head`, `merged_at` and `verdicts`
   alone; the renderer stays a pure function of the facts file with the same imports.
2. **Unknown is not a miss.** A `head` or `verdicts` the facts mark `"unknown"` (or that are absent) print no line (Q-K4-188).
3. **SPEC-0011 rule 10 is amended** (`proposed-spec-amendments-15.md` item 3, applied here).
4. **Fixtures**: the `kinds` report fixture's recorded clearances for pull requests 5 to 7 now name their heads (they were placeholders that named no head); pull request 8 keeps a
   clearance of another commit on purpose. The report goldens are regenerated and read: `kinds` shows one line (#8); `facts-pr-states` (from SPEC-0009's recorded pull
   requests) shows the merged pull requests with no verdict. `dirty-unknown` shows #8.
5. **Tests** (`tests/kit/test_product_report.py`): a clearance naming the head by a short sha, upper case or the whole head is no risk; an earlier clearance with a later one for
   another commit is reported and the reverse is not; only `fix` verdicts or a `cleared` with no sha are reported; no verdict; an open, a closed and an earlier merge are not
   checked; unknown verdicts or head print nothing; the lines come after the drift line in order.
6. **Kit 0.24.0**: manifest, hashes, plugin version (`product_report.py` is installed).

## Consequences

- The first weekly report after this shows any pull request that was merged without a verdict for its last commit, which is the miss the architect role cannot prevent (SPEC-0013 residual).

## Questions

| Q | Question | Reading taken |
| --- | --- | --- |
| Q-K4-188 | A merged pull request whose `head` or `verdicts` are `"unknown"` or absent. | No line: the report does not claim a miss it cannot read; the unknown shows elsewhere (the Cost line prints unknown fix verdicts). |
| Q-K4-189 | Only `fix` verdicts, or a `cleared` with no sha, on a merged pull request. | The "before its last commit was cleared" text (it has verdicts, none clears the head). |
| Q-K4-190 | Where among the At-risk lines. | After the drift line, as the amendment lists it fifth. |

## Residual

- 2026-10-19: the report shows the miss after the merge; nothing prevents it (SPEC-0013 rule 18, by design).

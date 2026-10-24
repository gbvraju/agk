# ADR-0080: the measured clearance of a covered final commit (REQ-028 part L3c, SPEC-0021), kit 0.45.0

- Status: Accepted
- Date: 2026-10-23
- Deciders: maintainers
- Related: ADR-0067, ADR-0068, ADR-0079
- Requirements: REQ-028

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`, `.claude-plugin/`, `agk.toml`

## Context

SPEC-0021 (Approved) lets a fix list that names only the final commit clear that commit in advance; L3b (kit 0.44.0) built the check before the merge. Rule 7 makes the measurements agree: the metrics, the facts
and the weekly report must count a covered final commit as a cleared head, or the At risk line "merged before its last commit was cleared" would report a pull request that was cleared. The 12 pull requests merged
since kit 0.35.0 (#118 to #129) were all merged on a head named by a `Verdict: cleared`, so no value changes today; one fix list with a real path (`8ecafb4` on #129) is the only covered form so far. The tests were
written first and run on unchanged `main` (15 failed; the output is in the pull request body).

## Decision

1. **The reading**: `metrics.merged_head_cleared(src, head, comments, authors)` is `yes` when a `Verdict: cleared <sha>` by a listed author names the merged head, as before, or when the merged head is the covered
   commit of the latest verdict by a listed author (`covered_head`): the record `commit-<head>` has one parent that starts with the reviewed sha and exactly the named files, each `modified`, whose patch changes
   exactly the named `- Status:` lines. A commit record is read only when it is needed. `no` for any other shape; `unknown` when no verdict by a listed author exists (as before) or the record cannot be read.
   `metrics.latest_verdict_body` is shared with `check_final_clearance.py`.
2. **The requirements case** (ruled in the verdict on #130): when a covered final commit changes `docs/requirements.md`, the section cannot be confirmed from the patch, so the value is `unknown` for that pull
   request; there is no extra read.
3. **The facts**: a merged pull request gains the optional `head_cleared` (the same value, `yes`, `no` or `unknown`); `schema` stays 1 and `kit/facts-schema.json` allows the field (Q-K4-220, ruled as read). A
   facts document without it is read as before. Two facts goldens gain the field.
4. **The report**: the At risk line is not printed for a pull request whose `head_cleared` is `yes`; for `no`, `unknown` and an absent field it is decided as before (Q-K4-232).
5. **Amendment 42** (`docs/runs/proposed-spec-amendments-42.md`) is applied to SPEC-0007 rule 8, SPEC-0009 rule 14 and SPEC-0011 rule 10.
6. **Tests, first** (`tests/kit/test_head_cleared.py`, new, installed): the covered commit as a cleared head, each refusal, a stranger's fix list, a named cleared verdict that needs no record, a later verdict, the
   requirements case, an unreadable record, the metrics table through the command line, the facts field and the report line; and in `tests/kit_dev/test_facts_wiring.py` the schema file.
7. **Kit 0.45.0**: the manifest `kit_version`, the hashes, the plugin version and `version` in this repository's `agk.toml` (ADR-0050 decision 7). The residual line of #130 (the check passes unchecked for a head
   two or more commits after the reviewed sha) stays open: it is tightened by a later change, now that the covered form is measured.

## Consequences

- A pull request merged on a covered final commit is a cleared head in the metrics, the facts and the report, without a second `cleared` verdict.
- A covered final commit of `docs/requirements.md` reads `unknown`, so the At risk line can still appear for it until a `Verdict: cleared` names the head.

## Questions

| Id | Question | Reading taken |
| --- | --- | --- |
| Q-K4-232 | When `head_cleared` is `unknown`, does the At risk line "merged before its last commit was cleared" print? | It is decided as before (printed when no `Verdict: cleared` names the head, not printed when the facts could not read the verdicts or the head): only `yes` removes the line. Proposed for ruling. |

## Residual

None.

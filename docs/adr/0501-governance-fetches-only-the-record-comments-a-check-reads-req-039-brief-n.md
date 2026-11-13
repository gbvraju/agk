# ADR-0501: Governance fetches only the record comments a check reads

- Status: Proposed
- Date: 2026-11-13
- Deciders: maintainers
- Related: ADR-0277, ADR-0293, ADR-0480, brief #557, brief #601, brief #1181, plan #661
- Requirements: REQ-039

Protected classes: `scripts/agk/`, `tests/kit/`, `kit/`

## Context

The governance workflow's `Record comments` step (kit repository only) GETs the Final comment of every SPEC-0021
rule 3a record that `check_adrs.py --record-ids` prints: 142 on 2026-11-13, about 140 of the about 150 API calls of a
run, on every pull request and every push. Only two checks read those comments: `check_protected_changes.py`, for the
ADR that a body's `Covered-by:` line names when its file still says `Proposed`, and `check_release.py`, only for a
release pull request (a version of `agk.toml` other than the merge base's, in flow mode). Between 05:30 and 06:30 IST
on 2026-11-13, with about 6 pull requests active, governance used about 2,700 of the workflow token's calls and the
token's limit was hit at 06:26 IST (and at 02:10 IST the night before), turning pull requests red.

## Decision

1. `check_adrs.py --record-ids` takes an optional `--body FILE`, the pull request body. With it, it prints:
   - every record's id when `check_release.reads_records` is true: flow mode, `check_release.py` on the merge base,
     and a version of `agk.toml` other than the merge base's. That one function is the test `check_release.check`
     and `check_release.valid_release` already made, now named and shared, not copied;
   - else the ids of the records (in HEAD's history or the merge base's) of each ADR that a `Covered-by: ADR-nnnn`
     line of FILE names;
   - else nothing.
2. Without `--body` it prints every id, as before. A body that cannot be read, or a base that does not resolve,
   also prints every id: narrowing never makes a check read less than it needs.
3. The checks are unchanged and still fail closed: a needed comment that is not in the file counts for nothing.
4. The workflow change, adding `--body "$RUNNER_TEMP/pr-body.md"` to the `--record-ids` call (the `PR body file`
   step already runs before it and writes an empty body on a push), is the owner's commit; a session never changes a
   workflow.
5. No spec rule says the workflow fetches every record: SPEC-0021 rule 3a names no fetch, and SPEC-0039 rule 6
   (amendment 122) describes the after-merge run of `merge_cleared.py`, which keeps fetching every record of the
   merge commit's history. No amendment is written.

## Consequences

Once the workflow passes the body, a governance run on an ordinary pull request or a push makes about 140 fewer API
calls, a `Covered-by:` build one record GET, and a release every one as today. Projects never run the step (no
`kit/agk-kit.mk`), so installed checks behave as before.

## Residual

- 2026-11-13: `merge_cleared.py`'s after-merge and pinned-merge runs still GET every record with the conductor's
  token; narrowing them by the same rule is a later brief (due 2027-01-31).

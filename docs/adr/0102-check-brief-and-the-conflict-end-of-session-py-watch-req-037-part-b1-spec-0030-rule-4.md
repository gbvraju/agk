# ADR-0102: `check_brief.py` and the conflict end of `session.py watch` (REQ-037 part b1, SPEC-0030 rule 4)

- Status: Accepted
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0100, ADR-0098
- Requirements: REQ-037

Protected classes: `kit/`, `scripts/agk/`, `tests/kit/`

## Context

SPEC-0030 (Approved, #167) rule 11 and the verdict on #169 split build (b): this is (b1), rule 4 and one end of `watch` that the verdict ordered. The tests were written first (`tests/kit/test_check_brief.py`, new cases in `tests/kit/test_session.py`; on the unchanged tree: 20 failed, 27 passed).

## Decision

1. **`check_brief.py FILE`** (installed, verbatim): prints `ok brief` or `FAIL brief: rule 4: ...` naming what is missing and never the sentence; it imports `brief_problems` from `session.py` (ADR-0100), the function `session.py next` applies, so the two cannot differ; it makes no network call. It takes a file, so it is not a step of the governance recipe (like `check_pr_body.py`).
2. **`watch --pr N` ends with `conflict #N`** when `mergeable_state` is `dirty` (amendment 52, the verdict on #169).
3. Flow mode: no version bump, one line under `## Unreleased` of `CHANGELOG.md`, manifest and hashes refreshed. Amendment 52 (`docs/runs/proposed-spec-amendments-52.md`) is applied to SPEC-0030.

## Consequences

- A brief can be checked locally before it is filed; a session sees a conflict without a person noticing that CI never started.

## Residual

None.

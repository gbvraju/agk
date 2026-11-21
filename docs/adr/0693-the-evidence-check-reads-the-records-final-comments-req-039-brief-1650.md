# ADR-0693: The evidence check reads the records' Final comments

- Status: Proposed
- Date: 2026-11-21
- Deciders: maintainers
- Related: ADR-0233, ADR-0293, ADR-0605, ADR-0656, SPEC-0021, brief #1650, plan #661
- Requirements: REQ-039

## Context

`scripts/agk/evidence.py check --body FILE` gives governance the pull request body (ADR-0656), but not the Final comments
of the base's SPEC-0021 rule 3a records. `check_protected_changes.py` counts an ADR Accepted by its Final record only
when the file `AGK_RECORD_COMMENTS` names holds that record's comment; `prepush.py` (ADR-0293) and `merge_cleared.py`
fetch the comments and set the variable, the evidence check did not. So a head whose `Covered-by:` ADR is Accepted only by
its record agreed in the builder's prepush and differed in the conductor's check: `Verdict: cleared 0450b8fe` on #1639
read `Evidence check: differs ... governance FAIL` on rule 3a alone, and main stayed red until the owner posted an accept.
ADR-0233 decision 5 says the check "makes no network call"; ADR-0605 already added the notes fetch.

## Decision

1. When the body given with `--body` has a `Covered-by:` line, the check fetches the Final comment of each rule 3a record
   on the record's `base` with prepush's own function (`prepush.fetch_record_comments`, one `gh api` GET each, imported,
   not copied), into a folder of its temporary folder, and adds `AGK_RECORD_COMMENTS` naming that file to the governance
   environment of ADR-0550 only; the file is removed with the folder. The sampled re-runs are unchanged. This amends
   ADR-0233 decision 5: besides ADR-0605's notes fetch, the check makes these GETs.
2. Comments that cannot be read (no GitHub origin, no `gh`, a failed GET) fail governance with prepush's
   `NO_RECORD_COMMENTS` line, naming the option, never the answer; the check differs, never a silent pass.
3. Without `--body`, with a body that has no `Covered-by:` line, or with no record on the base, nothing is fetched and the
   check runs as before. The caller's own `AGK_RECORD_COMMENTS` never reaches governance (the fixed list of ADR-0550).
   Nothing is cached: each check fetches afresh, so no file older than the head's base is read.
4. Settings: `execution = "local"` and GitHub mode behave the same (CI already reads the comments); personal mode
   (`forge = "files"`) runs no evidence check and has no Final records; `[testing]` settings are unchanged.

## Consequences

A head covered by an ADR Accepted only by its Final record reads `agrees` in the conductor's check, as in prepush, so it
needs no owner accept. Tests: `tests/kit/test_evidence.py`. Protected path classes changed: `scripts/agk/`
(`scripts/agk/evidence.py`) and `tests/kit/` (`tests/kit/test_evidence.py`).

## Residual

- 2026-11-21: a Final comment edited after the check's GET is read as it was then; the next check reads it again.

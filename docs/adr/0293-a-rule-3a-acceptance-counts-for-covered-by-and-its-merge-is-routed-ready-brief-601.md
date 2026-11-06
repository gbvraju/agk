# ADR-0293: A rule 3a acceptance counts for Covered-by, and its merge is routed ready (brief 601)

- Status: Proposed
- Date: 2026-11-06
- Deciders: maintainers
- Related: ADR-0271, ADR-0277, ADR-0284, ADR-0186, SPEC-0021, SPEC-0039, plan #542
- Requirements: REQ-028

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

Brief #601 found two gaps between ADR-0271 (`Covered-by:`, brief #545) and ADR-0277 (SPEC-0021
rule 3a, brief #557). First, `check_protected_changes.py` counts a `Covered-by:` ADR only when its
file says `- Status: Accepted` on the merge base, but an ADR accepted by a rule 3a `Final:` keeps
`Proposed` in its file until the release flips it, so it cannot cover a later build until then
(Q-598-1 on #598, where ADR-0285 was refused). Second, the router (`route.py`) reads the latest
verdict's first line, `Verdict: fix list <sha>`, and keeps `agk:fix` on a head that a covered rule
3a Final cleared and `merge_cleared.py` merged (#577 and #581). `Covered-by: ADR-0277` cannot
cover this change for the first reason, so this ADR is written in the old way (decision D1 of the
brief).

## Decision

1. `check_protected_changes.py`: when the `Covered-by:` ADR's own status on the merge base is not
   `Accepted`, the ADR still counts as Accepted when a rule 3a record of it is in the merge base's
   history and its Final comment, among the comments of `--comments FILE`, verifies it
   (`check_adrs.verified_records`, the reader that `check_adrs.py --pending` and the release check
   use). Without `--comments`, while the base holds a record of that ADR, the check fails with one
   line naming rule 3a and the option `--comments` (fail closed); with no record of it, the
   failure is the one of ADR-0271. An ADR whose file says `Accepted`
   needs no comments, as before. Every other condition of ADR-0271 is unchanged. The governance
   workflow already passes the comments that its `Record comments` step saves; no workflow
   changes.
2. `route.py`: a pull request's head counts as cleared for the label when the latest verdict by a
   listed author is a covered fix list whose sha is the full head, whose every `Final:` line
   accepts an ADR (`common.final_accepts`) and each named ADR is one that the pull request adds or
   modifies: the cases that `merge_cleared.py` clears (its `accepted_adrs` and the file test of
   its `hold_list`). Such a head is routed `agk:ready` (or `agk:approve` while a spec approval
   waits), and so a pull request merged on it ends with `agk:ready`. The order of the labels and
   every other case are unchanged.

3. The after-merge run (the conductor's fix list on 322b838, answering Q-601-1). Before its
   governance run, `merge_cleared.py` fetches the Final comment of each rule 3a record in the
   merge commit's history (the ids that `check_adrs.py --record-ids` prints there, read by the
   command's own `common.final_records`), one GET each, the GETs of the workflow's `Record
   comments` step, leaving out one that cannot be read, writes them to
   `<scratch>/home/record-comments.json` and adds `AGK_RECORD_COMMENTS=<that file>` to the
   `env -i` list. No token or other variable is passed, and the file goes with the scratch folder.
   `check_protected_changes.py` and `check_release.py` read the file that `AGK_RECORD_COMMENTS`
   names when `--comments` is absent; a given `--comments` wins. This amends ADR-0284 decision 2
   (the list of exactly `PATH`, `HOME` and `AGK_PR_BODY`). SPEC-0039 rule 6 changes by amendment
   122 (`docs/runs/proposed-spec-amendments-122.md`, the number the conductor reserved in that
   fix list), applied to the spec in this pull request; it needs a person's `Approve: SPEC-0039`.
4. `prepush.py` (ADR-0186): when the body file has a `Covered-by:` line and the base holds a rule
   3a record, its governance step fetches the same comments (`gh api --method GET`, one each)
   into a temporary file outside the checkout, passes it as `AGK_RECORD_COMMENTS` (the step runs
   `make`, which takes no `--comments`) and removes it afterwards. When any comment cannot be read
   (no GitHub origin, no `gh`, or a failed or non-JSON answer), the step fails closed with one
   line naming rule 3a and the option, and `make` does not run.

## Consequences

A build of an Approved spec can name an ADR accepted by a Final in its `Covered-by:` line on the
next pull request, without waiting for the release. CI, prepush and the after-merge run of
`merge_cleared.py` read the same Final comments, so such a line no longer passes CI and then
raises a false red after the merge. A local run that cannot read them fails, naming the option.
The router no longer leaves `agk:fix` on a pull request that the conductor merged on a rule 3a
Final.

## Residual

- 2026-11-06: the router does not read each ADR's status at the head, which `merge_cleared.py`
  checks with one GET each before it merges; a head whose named ADR is no longer `Proposed` is
  labelled `agk:ready` and still held by `merge_cleared.py` (due 2026-12-31).

# ADR-0724: A hand-merged decision is named by doctor and accepted at release on the owner's yes (REQ-035)

- Status: Proposed
- Date: 2026-11-22
- Deciders: maintainers
- Related: ADR-0277, ADR-0575, ADR-0710, SPEC-0021, SPEC-0028, brief #1738, brief #1735, plan #661
- Requirements: REQ-035

Protected classes this pull request changes: `scripts/agk/` (`doctor.py`, `check_adrs.py`, `changelog_fragments.py`,
`check_release.py`, `check_protected_changes.py`),
`kit/` (`templates/runtime/builder.txt`), `tests/kit/` (`test_check_adrs.py`, `test_doctor_lost_record.py`) and
`tests/kit_dev/` (`test_changelog_fragments.py`). `kit/hashes.json` is not edited by hand.

## Context

SPEC-0021 rule 3a reads an `ADR-nnnn Accepted (Final <id>)` record only from a squash commit that `merge_cleared.py`
made (`common.final_records`): first-parent, one parent, a subject ending `(#n)` and the line `Merged-by:
merge_cleared.py`. A pull request merged with the GitHub button carries no record, so the release (ADR-0710) never
accepts its decisions and nothing says so. On main at ba8e3a44 (2026-11-22), 30 decisions whose Final verdict cleared a
hand-merged pull request still read `Proposed`, ADR-0712 (#1719) among them. The owner answered Q-1738-1: a release
accepts a hand-merged decision when the Final verdict named the merged head.

## Decision

1. `doctor.py` prints one information line `lost-record: #<n> ADR-<nnnn>[, ADR-<nnnn>] merged without the merger (the
   release cannot accept it)` for each first-parent squash commit `(#n)` with one parent and no `Merged-by:` line that
   adds or changes an ADR the default branch reads `Proposed`, when that pull request's latest verdict by a record
   author (`check_adrs.record_authors`) is a covered fix list whose `Final:` lines accept ADRs the default branch reads
   `Proposed` and no record accepts. A read of the comments that fails prints `lost-record: #<n> unknown (cannot be
   read)`. The commits come from local `git`; only those pull requests' comments are read, with GET. It is a warning
   and changes no exit code.
2. `check_adrs.py --pending` and `changelog_fragments.py accept` take `--pulls FILE`, the merged pull requests'
   payloads as `GET pulls/<n>` returns them (a JSON list or the payloads one after another). With it, an ADR of such a
   hand-merged pull request is listed, and flipped, only when its Final comment in `--comments FILE` verifies
   (`final_record_verified`), it is that pull request's latest verdict by a record author in FILE, the payload says
   `merged: true`, its `merge_commit_sha` is that squash commit and its `head.sha` is the head the verdict names.
   Without `--pulls` nothing changes. A file that is not such a list is refused naming the option, and nothing is
   written.
3. The release pull request's own check (Q-1738-2, the maintainer's answer). The release body carries one line per
   hand merge it accepts, `Hand-merged: #<n> Final <id>`, written after `accept --pulls` passes. `check_adrs.py
   --record-ids --body FILE` also prints those Final ids, and `check_adrs.py --hand-merged --body FILE` prints each
   `<n>`, both offline. `check_release.py --body FILE --pulls FILE` lets the release flip an ADR named by such a line
   only when all of these hold: the Final verifies on #<n> (`final_record_verified`); the payload says `merged: true`;
   its `merge_commit_sha` is a one-parent commit of the base's first-parent line whose subject ends `(#<n>)`, with no
   `Merged-by:` line; its `head.sha` is the head the Final verdict names; and the ADR reads `Proposed` at the base and
   only its Status line changes. A `Hand-merged:` line without `--pulls`, or one whose payload is missing or does not
   match, fails closed, naming the option and never a value. A body with no such line checks as before.
   `check_protected_changes.py` takes `--pulls FILE` too and passes it, with the body, to the release exemption
   (`check_release.valid_release`). This pull request changes no workflow. The governance lines that fetch `GET
   pulls/<n>` and pass `--body` and `--pulls` are given to the owner in the pull request body, and the owner applies
   them after the merge.
4. A record is still read only from the merger's squash commit; a copied record line in a hand merge's message is
   still not a record. No session edits a Status line. The merger, the router, the guards and spec approval records
   (the brief's Q-2) are unchanged.

## Consequences

- The 30 decisions are named by doctor today and accepted by the next release that passes `--pulls`, not by this pull
  request.
- With `[flow] auto_merge = false` every merge is by hand, so doctor lists each one and `--pulls` is what lets those
  releases accept them.

## Residual

- The latest verdict is read from the comments the release gives in `--comments FILE`: a newer verdict left out of
  that file is not seen. The builder's release line names the file it must hold. The release pull request's own
  check verifies the named Final and the payload, not that it is the latest verdict. The builder's `accept --pulls`
  run checks that, and the conductor reviews the release.
- Until the owner applies the workflow lines, a release that carries a `Hand-merged:` line goes red in governance
  (fail closed), and a release without one is unchanged.

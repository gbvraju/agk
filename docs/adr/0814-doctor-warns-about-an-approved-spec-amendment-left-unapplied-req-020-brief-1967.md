# ADR-0814: Doctor warns about an approved spec amendment left unapplied for more than a day

- Status: Proposed
- Date: 2026-11-26
- Deciders: maintainers
- Related: ADR-0017, ADR-0724, ADR-0813, brief #1967, brief #1900, brief #1966, plan #661
- Requirements: REQ-020

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

An amendment the owner approves (`Maintainer answer: amendment <n> approved`) is applied to its spec by a later docs pull
request, which closes the amendment file with an applied line. Nothing in the kit listed an approved amendment left
unapplied: on 2026-11-26 nine sat unapplied (226 to 252), and briefs #1798 and #1900 each found the gap by hand. The
approval lives in comments, not files, so a governance check, which reads no network, cannot see it; `doctor.py` reads
GitHub with GET and already has the same shape of check (`brief-finished`, `lost-record`).

## Decision

1. **The reader.** `check_amendments.applied(text)` is true when an amendment file holds an applied line of either form
   on the default branch: brief #1900's `<date> (from date -u), brief #<n>: items <list> applied to <spec path> word for
   word` and SPEC-0073 build (c)'s `Applied (<date>, from date -u): items <list> to <spec path>, word for word`, matched
   across a wrapped line. `check_amendments.approval(comments, answerers, n)` returns the time of the first comment by
   an answerer (`session.owner_people`) whose first line is `Maintainer answer: amendment <n> approved`, or a settled
   line that `settled_keys` accepts, and None when there is none or a later `Correction:` by an answerer names the
   amendment. Files and data only.
2. **The warning.** `doctor.py` gains `amendment-unapplied` (`warn`). It reads, on `origin/<default_branch>` as
   `lost_ref` finds it, each `docs/runs/proposed-spec-amendments-<n>.md` added in the last 30 days
   (`AMENDMENT_DAYS`), newest first, and keeps the 20 newest with no applied line (`AMENDMENT_FILES`, so at most 20
   comment reads); for each it reads the comments of the adding pull request (the `(#n)` of its adding commit's
   subject, `pull_comments`) and lists `amendment <n> (#<pr>)` when its approval is older than a day
   (`FINISHED_AFTER`). Its fix: apply each listed amendment word for word in a docs pull request and close its file
   with the applied line (brief #1900). A file whose adding commit names no `(#n)` is counted as `unread <k>`.
3. **Never a false ok.** A comment read that fails is `cannot-check` with its reason class, and more pages than
   `LOST_PAGES` is `comments-unbounded`. No answerer listed in `config/reviewers.yaml` is `no-answerer`, and an
   amendment file in the tree with no default branch to read is `no-default-branch`; each hint names the setting, never
   a value. A project with no amendment file to read, and a sidecar (`[personal] forge = "files"`), are `ok`.
4. **Settings.** No new setting (`Q-AA-5`: the bounds are constants, as `LOST_PAGES` is). In `review_mode = "solo"`
   an approval counts only as the whole first line; in `team` the line may go on after the approval. With
   `[steward] settle_amendments` on, a settled line counts through `settled_keys` at the file's text; off, it does not.
   `pr_mode` and `execution` change nothing. `paused = true` prints the paused line only, as before.

## Consequences

An approved amendment left unapplied shows in `doctor.py` within a day. It is a warning: a listed amendment makes the
exit 4 as every warning does, and nothing is blocked (`Q-AA-4`: it does not stop a new amendment of the same spec).
ADR-0017's checks and exit codes are met, not changed. No workflow, label, ruleset or required check changes.

## Residual

- 2026-11-26: the steward's daily list naming the check's lines is the steward's own work (brief #1967 answer 6).

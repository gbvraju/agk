# ADR-0277: A Final line accepts an ADR without a status commit, and decisions take one file each (brief 557)

- Status: Proposed
- Date: 2026-11-05
- Deciders: maintainers
- Related: ADR-0263, ADR-0265, ADR-0266, SPEC-0009, SPEC-0021, SPEC-0028, SPEC-0034, SPEC-0039, plan #542
- Requirements: REQ-028, REQ-046, REQ-018

Protected classes: `scripts/agk/`, `tests/kit/`, `tests/kit_dev/`, `.claude/`, `CLAUDE.md`

## Context

Plan #542 and the owner's direction of 2026-11-05 ask that a small change stop taking a day. Brief
#557 measured why one-line pull requests took 12 to 14 hours on 2026-11-04 and 05: after the
conductor's `Final:` line the builder made a status commit, which started another CI round and asked
for another look; and adjacent appends to `docs/runs/decisions-log.md` made parallel pull requests
conflict, about six re-merges in a day. This ADR number and amendment 118 were reserved for the brief
by the conductor. This pull request carries items 1 and 2 of the brief; items 3 to 5 and the
requirements half of item 2 are later builds (the pull request's `Questions:`).

## Decision

1. **A Final line accepts an ADR (SPEC-0021 rule 3a, amendment 118).** When the latest covered fix
   list by a listed verdict author names the pull request's head itself, and every `Final:` line is
   `docs/adr/<file> Proposed -> Accepted`, that comment is the ADR's acceptance and no status commit
   follows. `common.final_accepts` is the one reader.
   - `check_final_clearance.py` fails, naming rule 3a, when a named ADR is not `Proposed` at the
     head.
   - `merge_cleared.py` treats it as a clearing verdict only when the fix list's sha is the full
     40-character head, reads each named ADR at the head (one GET each) and holds unless every one
     is `Proposed`; it then merges with the squash commit message line
     `ADR-nnnn Accepted (Final <comment id>)` per ADR. Every hold of SPEC-0039 rule 5 still applies.
   - `check_adrs.py` reads those message lines from the base's history: an ADR so recorded is
     Accepted for the immutability rule (only its Status line may change), and
     `check_adrs.py --pending` prints the ones whose file still says `Proposed`. The release pull
     request, which already batches changes, makes the one-line flips.
   - The metrics count a head merged under such a fix list as cleared (`merged_head_cleared`).
   - Any other `Final:` (a spec, a requirement, another status, a mix, or a stack-options ADR, whose
     `Chosen` line and acceptance go in one commit) keeps today's path: the builder's status commit,
     checked by rule 3.
   - A Final accepts only an ADR that the pull request adds or changes: `check_final_clearance.py`
     reads `git diff` from the merge base (failing closed without a base), and `merge_cleared.py`
     reads the pull request's files, so a Final on an unrelated pull request cannot accept a
     Proposed ADR that waits on the default branch. A newer `Verdict:` hides an older accept.
   - The record is read only from a squash commit that `merge_cleared.py` made: on the base's
     first-parent line, one parent, a subject ending `(#n)` and the line
     `Merged-by: merge_cleared.py` (`check_adrs.final_records`). `facts.py` reports the ADR as
     `Accepted` only after it reads the comment of the record's id and finds it on the record's pull
     request, by a listed verdict author, accepting that ADR (`check_adrs.final_record_verified`);
     without GitHub nothing is verified and the file's status stands. A copied message therefore
     accepts nothing in the owner's view; offline, it can only make an ADR immutable or ask the
     release for a flip, which the release's reviewer compares with the facts.
   - The release pull request flips each recorded ADR's Status line to `Accepted` and nothing else
     (SPEC-0028 rules 4 and 5 as amended); `check_release.py` fails a release that leaves one
     `Proposed`. The drift audit raises no stale-`Proposed` finding for a recorded ADR.
2. **One file per decision (SPEC-0009 rule 13, SPEC-0034 rule 19, amendment 118).** A new
   decisions-log row goes to `docs/runs/decisions/<YYYY-MM-DD>-<id>.md`, one table row per file;
   `docs/runs/decisions-log.md` is frozen at its length (`check_specs.py` fails a change to it, while
   creating it, as init and adopt do, passes), the intake accepts a new file of the folder in place
   of rows in the old log, and the writers' guidance (`CLAUDE.md`, `.claude/agents/architect.md`,
   the getting-started and product-owner guides) points to the folder. `common.log_lines`, and so
   `find_questions`, `check_specs.py` and `facts.py`, read the old log first and then the folder in
   sorted order; the old file is never rewritten. `check_specs.py` fails a file of the folder that is
   misnamed or does not hold exactly one row, and `check_pr_body.py` lets a `Brief: none (spec)`
   change carry the folder beside it, as it does the old log.
3. `.claude/agents/conductor.md` says that a `Final:` accept on the head needs no status commit and
   that the conductor then merges as for `Verdict: cleared`.

## Consequences

- A pull request whose only remaining step is an ADR's acceptance merges in the CI round it already
  has: one round instead of two or three.
- The same person decides by the same comment; the record moves from a status commit to the squash
  message, and the file says `Proposed` on the default branch until the next release flips it.
  The facts (and so the product report) read the verified record and show it as `Accepted`;
  `check_adrs.py --pending` names each file still to flip.
- Parallel pull requests that record decisions no longer touch the same lines.

## Residual

- 2026-11-05: requirement entries in `docs/requirements.d/` (the rest of item 2) need a new protected
  path class and every reader of `docs/requirements.md`; a later build (due 2026-11-30).
- 2026-11-05: items 3 (an approval survives a merge of main), 4 (scoped checks) and 5 (lead times)
  of brief #557 are later builds (due 2026-11-30).
- 2026-11-05: until the release pull request flips them, an ADR accepted by a Final reads `Proposed`
  in its file; `check_adrs.py --pending` is the list and `check_release.py` fails a release that
  leaves one (due 2026-12-31).
- 2026-11-05: the offline readers (`check_adrs.py`, the drift audit, the release check) cannot read
  a comment, so they trust the squash record of `merge_cleared.py`; only `facts.py` verifies the
  comment id (Q-557-4, due 2026-11-30).

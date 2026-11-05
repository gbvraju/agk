# ADR-0277: A Final line accepts an ADR without a status commit, and decisions take one file each (brief 557)

- Status: Proposed
- Date: 2026-11-05
- Deciders: maintainers
- Related: ADR-0263, ADR-0265, ADR-0266, SPEC-0009, SPEC-0021, SPEC-0039, plan #542
- Requirements: REQ-028, REQ-046, REQ-018

Protected classes: `scripts/agk/`, `tests/kit/`, `.claude/`

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
   - Any other `Final:` (a spec, a requirement, another status, a mix) keeps today's path: the
     builder's status commit, checked by rule 3.
2. **One file per decision (SPEC-0009 rule 13, amendment 118).** A new decisions-log row may go to
   `docs/runs/decisions/<YYYY-MM-DD>-<id>.md`, one table row per file. `common.log_lines`, and so
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
  Readers of the file alone (the facts' ADR list, the product report) show it as `Proposed` until
  then; `check_adrs.py --pending` names each one.
- Parallel pull requests that record decisions no longer touch the same lines.

## Residual

- 2026-11-05: requirement entries in `docs/requirements.d/` (the rest of item 2) need a new protected
  path class and every reader of `docs/requirements.md`; a later build (due 2026-11-30).
- 2026-11-05: items 3 (an approval survives a merge of main), 4 (scoped checks) and 5 (lead times)
  of brief #557 are later builds (due 2026-11-30).
- 2026-11-05: until the release pull request flips them, an ADR accepted by a Final reads `Proposed`
  in its file; `check_adrs.py --pending` is the list (due 2026-12-31).

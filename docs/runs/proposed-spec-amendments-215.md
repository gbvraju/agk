# Proposed spec amendments 215 (SPEC-0050; REQ-057)

Date: 2026-11-22 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0718 (brief #1714), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0050-overlapping-work-never-runs-at-once-and-a-second-change-re-proves.md` (rule 7a and question
`Q-S0050-16`). Brief #1714 reserved its number at take; 214 is held by pull request #1721, so this file takes 215. It
proposes the lines and does not edit the spec. A later pull request applies them word for word, on a person's
`Approve: SPEC-0050` on it; no session posts it.

The sentence (brief #1714): "A covered fix list whose only `Final:` lines accept the pull request's own ADRs carries to
the light re-prove's merge of the default branch, as a plain clearing verdict does, and its ADRs are still accepted in
the squash, so a shared-index merge never sends a cleared head back for review."

## What is on the default branch today

Read in the code by this session on main at f1d2f05 (2026-11-22): `merge_cleared.judge_carried` carries only
`Verdict: cleared <old>`, and `accepted_adrs(verdict, sha)` returns None unless the fix list names the head itself, so a
head cleared by a covered fix list of SPEC-0021 rule 3a is held at its light merge with `the latest verdict does not
clear this head (rule 3)`.

## Items

1. **Rule 7a, the clause "a fix list with `Final:` lines never carries".** Replace it with: "a covered fix list on the
   first parent whose `Final:` lines all accept ADRs (SPEC-0021 rule 3a) carries the same way, and its acceptance lines
   are written in the squash as for the head it names, each ADR read as `Proposed` at the new head and one that the pull
   request adds or changes; a fix list with a numbered item or any other `Final:` line never carries, and a verdict
   carries over one light merge only (amendment 215)".
2. **`Q-S0050-16`, at its end.** Add: "Amendment 215 (brief #1714): a covered fix list that only accepts the pull
   request's own ADRs carries as a plain clearing verdict does; in local mode the new head still needs its own local
   evidence (rule 4 of SPEC-0039)."

No other rule changes.

# Proposed spec amendments 118 (SPEC-0021, SPEC-0039, SPEC-0009; REQ-028, REQ-046, REQ-018)

Date: 2026-11-05 (from `date -u`). Approved text changes only through a proposal like this one (principle 6). Written for
ADR-0277 (brief #557, plan #542), which stays `Proposed` for the maintainers' decision. The number 118 is the one the
conductor reserved on #557. Each item below is applied by the same pull request, as the brief asks; no rule weakens: an
acceptance still needs the same listed author's `Final:` line on the exact head, and every hold of SPEC-0039 rule 5 still
applies.

The owner's direction of 2026-11-05 on brief #557, quoted as data: "take a same stab on existing ones also where we can
bring speed and quality ... Currently it is taking too much time for a small line change also."

Files changed: `docs/specs/0009-facts.md`, `docs/specs/0021-when-a-fix-list-verdict-s-only-item-is-the-final-commit-and.md`, `docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`.

1. **SPEC-0021, new rule 3a ("A Final line that accepts an ADR").** Added after rule 3: when the latest covered fix list
   names the head itself and every `Final:` line is `docs/adr/<file> Proposed -> Accepted`, the comment is the ADR's
   acceptance and no status commit follows. `check_final_clearance.py` fails, naming rule 3a, unless each named ADR is
   `Proposed` at the head; `merge_cleared.py` clears that head and writes one squash message line
   `ADR-nnnn Accepted (Final <comment id>)` per ADR; `check_adrs.py` treats an ADR so recorded in the base's history as
   Accepted, and `check_adrs.py --pending` lists the ones whose file still says `Proposed`, which the release pull request
   flips; `merged_head_cleared` (rule 7) is `yes` for that head. Any other `Final:` line keeps rule 3.
2. **SPEC-0039 rule 3 ("A trusted verdict").** The sentence "A verdict for another head, a short sha, a verdict with more
   text on its first line (`Verdict: cleared <sha>, after ...`) and a multi-line fix list never merge." gains one
   exception: a covered fix list on the full 40-character head whose every `Final:` line accepts an ADR clears the head
   like `Verdict: cleared <sha>` when the command reads each named ADR at the head (one GET each) as `Proposed`; it holds
   naming rule 3 otherwise, and on a merge it passes the squash commit message, one line per ADR.
3. **SPEC-0009 rule 13 (`questions`).** "`true` when a row of `docs/runs/decisions-log.md` contains the text `<id> ruled`"
   becomes "`true` when a row of the decisions log contains the text `<id> ruled`; the log is
   `docs/runs/decisions-log.md` followed by the one-row files `docs/runs/decisions/<YYYY-MM-DD>-<id>.md` in sorted order".
   The old file is never rewritten. `check_specs.py` fails a file of the folder that is misnamed or does not hold exactly
   one table row, and `check_pr_body.py` lets a `Brief: none (spec)` change carry the folder beside it.
4. **Tests.** `tests/kit/test_final_accepts.py` (items 1 and 2) and `tests/kit/test_decision_files.py` (item 3).

Not in this amendment (later builds of brief #557, its pull request's `Questions:`): requirement entries in
`docs/requirements.d/` (a new protected path class), an approval that survives a merge of main (SPEC-0032 rule 5), scoped
checks for small heads and the lead-time measurement.

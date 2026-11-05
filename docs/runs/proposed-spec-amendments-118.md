# Proposed spec amendments 118 (SPEC-0021, SPEC-0039, SPEC-0009, SPEC-0034, SPEC-0028; REQ-028, REQ-046, REQ-018)

Date: 2026-11-05 (from `date -u`). Approved text changes only through a proposal like this one (principle 6). Written for
ADR-0277 (brief #557, plan #542), which stays `Proposed` for the maintainers' decision. The number 118 is the one the
conductor reserved on #557. Each item below is applied by the same pull request, as the brief asks; no rule weakens: an
acceptance still needs the same listed author's `Final:` line on the exact head, and every hold of SPEC-0039 rule 5 still
applies.

The owner's direction of 2026-11-05 on brief #557, quoted as data: "take a same stab on existing ones also where we can
bring speed and quality ... Currently it is taking too much time for a small line change also."

Files changed: `docs/specs/0009-facts.md`, `docs/specs/0021-when-a-fix-list-verdict-s-only-item-is-the-final-commit-and.md`, `docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md`, `docs/specs/0034-a-team-sets-how-many-builder-sessions-run-at-once-and-agk-ha.md`, `docs/specs/0028-in-flow-mode-a-kit-build-pull-request-does-not-bump-the-vers.md`.

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
4. **The conductor's fix list of 2026-11-05 on f623a77.** Each of items 1 to 3 gains:
   - SPEC-0021 rule 3a: each named ADR must be one that the pull request adds or changes (`git diff` from the merge base);
     a stack-options ADR never counts (rule 3 keeps its one commit); the record is read only from a squash commit of
     `merge_cleared.py` on the base's first-parent line (one parent, a subject ending `(#n)`, the line
     `Merged-by: merge_cleared.py`); `facts.py` reports the ADR `Accepted` only after it reads the comment of the
     record's id on the record's pull request, by a listed verdict author, accepting that ADR; the drift audit raises no
     stale-`Proposed` finding for a recorded ADR.
   - SPEC-0039 rule 3: each named ADR must be among the pull request's files (added or modified), and the squash message
     also carries the line `Merged-by: merge_cleared.py`.
   - SPEC-0009 rule 13: `docs/runs/decisions-log.md` is frozen at its length, and `check_specs.py` fails a change to it.
5. **SPEC-0034 rule 19 ("The append-only logs merge as a union").** The rule's open question is ruled: since GitHub's
   check does not honour `merge=union`, the decisions log takes one file per entry (SPEC-0009 rule 13 as amended), the
   old file is frozen and the intake records its rulings as such files; the union mark stays for the residuals and the
   catch logs.
6. **SPEC-0028 rules 4 and 5 (the release pull request and its check).** The release also sets to `Accepted` the Status
   line of each ADR that a Final line accepted (rule 3a), changing nothing else in it, and `check_release.py` fails a
   release that leaves one `Proposed`, or changes an ADR in any other way.
7. **Tests.** `tests/kit/test_final_accepts.py` (items 1, 2 and 4), `tests/kit/test_decision_files.py` (items 3 to 5),
   `tests/kit_dev/test_intake.py` (item 5) and `tests/kit_dev/test_release_check.py` (item 6).

Not in this amendment (later builds of brief #557, its pull request's `Questions:`): requirement entries in
`docs/requirements.d/` (a new protected path class), an approval that survives a merge of main (SPEC-0032 rule 5), scoped
checks for small heads and the lead-time measurement.

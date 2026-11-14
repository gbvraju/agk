# Proposed spec amendments 179 (SPEC-0043; REQ-050)

Date: 2026-11-14 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0520 (brief #1221), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md`. Brief #1221
reserved ADR-0520; the conductor reserved amendment 179 in its verdict on head 061ac8b (answer to `Q-1221-1`). This pull
request does not edit the spec; the maintainers apply the lines if they approve them.

The sentence (brief #1221): "Planning keeps open questions few and readable, and its render can be run again, so a large
source set does not bury business in thousands of questions or block a second pass."

## What is on the default branch today

Read in the code by this session on `origin/main` (76fcd1b): `scripts/agk/plan_intake.py render` writes new files only
and refuses when any of them exists (rule 7); it writes every open question and every unsettled conflict as its own
block of `Questions for business`, and `publish` prints one issue per block (rule 25 with ADR-0508); the OpenSpec reader
writes each cross-reference it cannot resolve as an open question (amendment 166, ADR-0473); `validate` has no limit on
the number of open questions.

## Items

1. **Rule 7, one added sentence after "a later render refuses to overwrite them".** "`render` also writes
   `docs/plan/render-digests.json`, the SHA-256 digest of each file it wrote under `docs/plan/` and the Draft spec it
   made for each feature area, and a first render refuses over an existing list as over its other files. `render
   --again` rewrites only a file the list holds whose bytes still have the listed digest, creates a file that does not
   exist, and leaves as it is, printing `kept <path>: <reason>`, a file a person edited or one the list does not hold; a
   listed area's Draft spec is written once and kept, a new area gets one, and without a readable list `--again`
   refuses and writes nothing."
2. **Rule 25, one added sentence after the `Questions for business` sentence of ADR-0508.** "Open questions of one kind
   (the text after `<section> <key>: `, else the whole text) and one area (the feature area holding the requirement the
   question names, else the file of its first source) are one question for business, keyed by the first of them, whose
   `Blocks:` line names the keys it holds; a cross-reference that names no one source heading is a `Note:` line of its
   requirement in `docs/plan/requirements-proposed.md` (the requirement's optional `notes`), never a question; and
   `validate` prints `warning: <n> open questions` when the questions for business are more than `[plan]
   max_questions` of `agk.toml` (a positive whole number, 60 when absent), with exit 0."
3. **Rule 6, amendment 166 item 4's cross-reference line.** "any other cross-reference (for example `design option
   a`) is one open question with `(verify)` at the requirement's heading that names the cross-reference's position" becomes
   "any other cross-reference (for example `design option a`) is one note of the requirement, with `(verify)`, that names
   the cross-reference's position (item 2)"; the rest of the line (`never its text`, `Q-1108-9`) stays.
4. **No other change.** Rules 3 to 5, rule 8 and the rest of rules 7 and 25 stay as they are.
5. **Tests.** `tests/kit/test_plan_intake_questions.py` (ADR-0520's Consequences).

# Proposed spec amendments 175 (SPEC-0043; REQ-050)

Date: 2026-11-14 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0516 (brief #1217), which stays `Proposed` for the maintainers' decision. The path:
`docs/specs/0043-a-project-s-plan-is-drafted-from-its-sources-and-tracked-with-calibrated-ranges.md`. The numbers 175 and
0516 are the ones brief #1217 reserved. The rule text is not written into the spec in this pull request, whose `Touches:`
does not name the spec. The owner decides it with `Approve: <head> SPEC-0043` on this pull request; no session posts that
line.

The sentence (brief #1217): "The plan trace counts every source document, so a document that no requirement cites can no
longer pass as covered."

## What is on the default branch today

Read in the code by this session on `origin/main` (76fcd1b):

- `scripts/agk/check_plan.py` `Plan.in_scope` counts the `In scope` locations of `docs/plan/scope.md` and the screen
  headings of a `Kind: design` source; `Plan.problems` fails only those of them that no requirement cites. A file under
  `docs/sources/` that neither names is never read by rules 10 and 11.

## Items

1. **Rule 10, one more failure.** "Once `docs/plan/` exists, each file under `docs/sources/` that has no location cited by
   a requirement's `Source:` line and resolving, and that no list line under `Out of scope` in `docs/plan/scope.md`
   names by its own path (no line or heading) with a reason, fails with one line `<file> is a source no requirement
   cites (list it out of scope or cite it)`, naming the file and never its text."
2. **Rule 9, one line per source.** "`--trace` prints, after the matrix, one line per source file
   `<file>: <a> of <b> headings or rows cited`: the headings outside fences and the table rows after a separator line of
   a Markdown file, or the non-blank lines after the header of a text file, a unit cited by `<file>#<heading>` or by
   `<file>:<line>` of its line. The line is information."
3. **No other change.** Rule 11's coverage line, rules 1, 2 and 20 to 22 and every workflow stay as they are.
4. **Tests.** `tests/kit/test_check_plan_uncited.py`, invented files in `tmp_path`, no network: an uncited source fails
   naming the file, never its text, and each uncited source fails once; listing it out of scope with a reason passes;
   a line without a reason, or an out-of-scope location of one line, does not; one resolving citation passes and the
   trace line shows `1 of 4`; a heading cited by name and by line counts once; a citation that does not resolve counts
   nothing; a project with no plan is not checked.

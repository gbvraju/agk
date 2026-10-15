# Proposed spec amendments 9 (SPEC-0003)

Date: 2026-10-15 (from `date -u`). Found by shadow review 2 (`docs/runs/shadow-review-2.md`); the implementation is
ADR-0013. Approved specs change only through a proposal like this one (principle 6). Nothing here is applied;
until the maintainers apply it, the code is ahead of the Approved text of the rules below.

## SPEC-0003 (`docs/specs/0003-reviewer-agent.md`)

1. **Rule 5, content of the context.** Now: (a) the PR body; (b) the diff; (c) the advanced requirements; (d) the
   protected classes touched; (e) the referenced specs and ADRs; (f) the principles. Proposed: (a) the PR body; (b)
   the diff; (c) the full current text of every changed file (a deleted file is named; a binary or oversized one is
   named as not shown); (d) the advanced requirements; (e) the protected classes touched; (f) the referenced specs
   and ADRs; (g) the principles; (h) the operating rules, the text of `CLAUDE.md`. Reason: a rule made wrong by a
   change can sit outside the hunk (#6), and the operating rules were absent (#22). The letters shift; the test
   docstrings that cite `rule 5(c)` to `5(f)` are updated when this is applied.
2. **Rule 6, caps.** Add: the changed-files section and the operating rules are capped by `review_other_cap`, like
   the other sections after the diff.
3. **Rule 7, missing inputs.** Add: a missing `CLAUDE.md` is listed under `Context problems`.
4. **Rule 11, scope.** The scope stays Approved text only. Add one item: for every Accepted ADR decision and Approved
   spec rule in the context, whether the diff, including its effect on other files, contradicts it; and a sentence:
   `CLAUDE.md` is context, not a source of rules to cite.
5. **Rule 12 and rule 21, the agent definition.** Rule 12: the prompt carries the item added to rule 11 and tells
   the agent to read the changed files in full. Rule 21: a test checks that the definition says both and that
   `CLAUDE.md` is context, not a source of rules to cite.
6. **Rule 18, fixtures.** Add `F11` an unchanged rule far from a change (shadow review 2, #6) and `F12` an installed
   check whose tests are not installed, with `CLAUDE.md` present (#22).
7. **Rule 19, context tests.** The sections appear in the order of rule 5 as amended; `CLAUDE.md` is always present
   in the context; a changed file appears in full, with a deleted, a binary and an oversized file handled as stated.

## Question

- Q-K2-25: the cross-file statement of rule 11 (item 4) is part of the agent's reasoning; the report format and the
  validator are unchanged, so nothing in the report records that every decision and rule was checked. Should the
  report carry a line for it (for example `Checked: ADR-0003 decisions 1-5; SPEC-0001 rules 1-24`) and the validator
  check that the cited documents exist in the context?

## Status

Proposed. Not applied.

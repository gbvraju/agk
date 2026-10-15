# ADR-0013: The reviewer sees CLAUDE.md and changed files in full

- Status: Accepted
- Date: 2026-10-15
- Deciders: maintainers
- Related: ADR-0011
- Requirements: REQ-013

## Context

Shadow review 2 (`docs/runs/shadow-review-2.md`) re-ran the reviewer on three pull requests where the maintainers had
findings on record, and it cleared all three. The diagnostic showed what the context lacked: for #6 the unchanged
CLAUDE.md rule 8 sat outside the hunk, so a rule made wrong by the change was not visible; for #22 the context held no
copy of CLAUDE.md at all, and the manifest, the new check and its tests were visible only as hunks. SPEC-0003 rule 11
limits the review to rules stated in Approved text; that scope does not change. What changes is what the reviewer
is given and asked to read.

Protected classes: `scripts/agk/`, `.claude/`, `tests/kit/`, `tests/kit_dev/`, `kit/`. This PR changes all five.

## Decision

1. **Operating rules.** `review_context.py` always includes the text of `CLAUDE.md` in a section `Operating rules`
   (after the principles); a missing CLAUDE.md is a context problem. It is context, not a source of rules to cite: a
   finding cites Approved text (a spec rule, an ADR decision, a principle or an acceptance criterion).
2. **Changed files in full.** A section `Changed files` (after the diff) holds the full current text of every changed
   file, in path order, within `review_other_cap` like the other sections; a deleted file is named, a binary or
   oversized one is named as not shown; a cut is marked and the header says `Truncated: yes`.
3. **The cross-file check.** `.claude/agents/reviewer.md` adds: for every Accepted ADR decision and Approved spec rule
   in the context, state whether the diff, including its effect on other files, contradicts it; a contradiction is a
   finding. The scope of rule 11 is unchanged. The statement is part of the agent's reasoning; the report format and
   the validator are unchanged.
4. **Fixtures.** F11 reproduces #6 (an unchanged rule far from a change) and F12 reproduces #22 (an installed check
   whose tests are not installed, with CLAUDE.md present). The tests show that the context contains what a reviewer
   needs to see; whether the agent notices is judged by the shadow reviews (rule 22), not by CI.
5. **Kit version** `0.6.1`: installed content changed (`scripts/agk/review_context.py`, `.claude/agents/reviewer.md`,
   the installed tests). The spec changes are in `docs/runs/proposed-spec-amendments-9.md`, applied on the maintainers' instruction in this PR.

## Consequences

- Contexts are larger. The 1500-line cap on the changed-files section can cut later files of a large PR (path order),
  and the report must then say the context was truncated.
- The reviewer can see a change next to the rule it breaks, and the operating rules of the project, without being
  allowed to cite anything but Approved text.
- SPEC-0003 rules 5, 6, 7, 11, 12, 18, 19 and 21 carry the change (amendments 9). The report carries no record of the
  cross-file check (no `Checked:` line); shadow reviews measure it.

## Residual

- 2026-10-15: the cross-file check is a prompt instruction; whether the agent follows it is measured only by shadow
  reviews (due 2026-11-30).
- 2026-10-15: the changed-files section is cut in path order, not by relevance (due 2026-12-15).
- 2026-10-15: class naming in an ADR is still a substring match (ADR-0003 residual).

# Proposed spec amendments 4

Date: 2026-10-14 (from `date -u`). Found while implementing overnight item E (ADR-0009). Approved specs change only
through a proposal like this one (principle 6). Nothing here is applied; maintainers decide.

## SPEC-0001 (`docs/specs/0001-agk-init.md`)

1. **Rule 19, the printed branch rules.** Now: "The text comes from `kit/templates/branch-rules.txt`; a test keeps it
   equal to the kit's ADR-0001 decision 3 (rule 23)." Proposed: "...; a test keeps it equal to the kit's ADR-0001
   decision 3 except that the phrase `The ruleset main` reads `The ruleset for the default branch`." Reason: the
   default branch can have any name, and this repository's ADR-0001 is immutable.

## SPEC-0002 (`docs/specs/0002-agk-adopt.md`)

2. **Rule 8, the branch-rule text.** Now: "`kit/templates/branch-rules.txt` keeps its text." Proposed: "`kit/templates/
   branch-rules.txt` says `ruleset for the default branch` (ADR-0009)."
3. **Rule 7, the refusal.** Now: "...else it refuses and asks the user to set it (exit 1)." Proposed: "...else it
   refuses (exit 1), names the path class `.git/refs/remotes/origin/HEAD` and the command
   `git remote set-head origin --auto`; adopt has no option to set the branch."

## Status

Applied 2026-10-15 on maintainers' instruction (final commit of the item E PR). SPEC-0001 rule 19 and SPEC-0002
rules 7 and 8 carry the proposed text; nothing else in either spec changed.

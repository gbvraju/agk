# Proposed spec amendments 6

Date: 2026-10-15 (from `date -u`). Found while implementing ADR-0010 (PR #20): init and adopt now print a scanner-exclusion
block after the ruleset, and neither Approved spec names it. Approved specs change only through a proposal like this one
(principle 6). This is Q-K2-19 of PR #20; the maintainers ruled yes.

## SPEC-0001 (`docs/specs/0001-agk-init.md`)

1. **Rule 19, the scanner-exclusion block.** Now: rule 19 describes the printed ruleset and repository settings only.
   Proposed: add "After the ruleset text init prints the scanner-exclusion block of
   `kit/templates/scanner-excludes.txt`: the bandit, flake8, pylint and mypy settings that exclude `scripts/agk`,
   `tests/kit` and `.claude/hooks`. It is printed only, nothing is written, and a test keeps the printed block equal to
   the template and to the README's \"Existing scanners\" section (ADR-0010)."

## SPEC-0002 (`docs/specs/0002-agk-adopt.md`)

2. **Rule 8, the matching adopt text.** Now: rule 8 says the printed ruleset instructions name the detected branch and
   that `kit/templates/branch-rules.txt` says `ruleset for the default branch` (ADR-0009). Proposed: add "After the
   ruleset text adopt prints the same scanner-exclusion block from `kit/templates/scanner-excludes.txt` (print only;
   adopt writes no scanner configuration) (ADR-0010)."

## Notes

- ADR-0010 is Accepted on the branch of PR #20; until that PR merges, the references to it above are ahead of main.

## Status

Applied 2026-10-15 on maintainers' instruction (this PR). SPEC-0001 rule 19 and SPEC-0002 rule 8 carry the proposed text;
nothing else in either spec changed.

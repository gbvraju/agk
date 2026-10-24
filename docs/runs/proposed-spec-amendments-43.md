# Proposed spec amendments 43 (SPEC-0012; REQ-032 part a)

Date: 2026-10-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0083. The path: `docs/specs/0012-intake.md`.

1. **SPEC-0012, the intake script.** `python3 scripts/agk/intake.py renumber <id> [--ref REF]` moves a pull request's own requirement, spec and ADR to the next free numbers on the default branch (SPEC-0025 rule 2):
   it renames the added files, rewrites the ids in them and in the lines the pull request added, changes nothing else, prints what it moved, refuses a dirty work tree or an id that is not the pull request's own,
   and a second run changes nothing.

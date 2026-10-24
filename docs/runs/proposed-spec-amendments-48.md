# Proposed spec amendments 48 (SPEC-0012, SPEC-0020; REQ-034)

Date: 2026-10-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0091. The paths: `docs/specs/0012-intake.md`, `docs/specs/0020-when-the-maintainers-answer-every-intake-question-before-the.md`.

1. **SPEC-0012, the intake script.** Every command of `intake.py` prints, as its first line of output, `intake: kit <version>`, the `kit_version` of `kit/manifest.json` above `scripts/` (SPEC-0027 rule 1). The command refuses,
   naming the rule and both versions, when that version is older than the version in the project's `agk.toml`, and prints a one-line note when it is newer (rules 2 and 3). `ids` prints its JSON on the lines after the first.
2. **SPEC-0020 rule 6, the answers are written down.** The opening paragraph may also say `The maintainers answered N question(s) at review, before approval` (N of 1 to 3) or `The maintainers gave N answer(s)
   before it was written` (any whole N from 1, for answers given in a brief or an issue); the older forms stay. No form is for a question answered after approval (SPEC-0027 rules 4 and 5).

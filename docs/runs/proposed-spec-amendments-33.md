# Proposed spec amendments 33 (listed verdict authors: SPEC-0001, SPEC-0007, SPEC-0009, SPEC-0011)

Date: 2026-10-21 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0068. The paths: `docs/specs/0001-agk-init.md`, `docs/specs/0007-metrics.md`,
`docs/specs/0009-facts.md`, `docs/specs/0011-inbox-and-report.md`.

1. **SPEC-0001 rule 12, `config/reviewers.yaml`.** The file may have an optional top-level `verdict_authors: [handle, ...]`; without it the user handle of `maintainers` is the only listed author, and
   `reviewers.py --check` fails when nobody is listed (SPEC-0021 rules 5 and 6).
2. **SPEC-0007 rule 4.** A verdict comment is a comment by a listed verdict author; a comment by anyone else is not a verdict (it was "any author"). When nobody is listed the verdict-dependent fields are
   `unknown`. The `merged_head_cleared` bullet reads "a `Verdict: cleared <sha>` comment by a listed author". Rule 5 (`review_rounds`) and `rejected` follow from rule 4.
3. **SPEC-0009 rule 14 and rule 16.** The `verdicts` item counts comments by listed authors and is the string `"unknown"` when nobody is listed; the table of reused readers names `metrics.verdict_authors`.
4. **SPEC-0011 rule 5.** A pull request "without a verdict" has no verdict by a listed author.

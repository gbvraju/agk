# Proposed spec amendments 44 (SPEC-0021, SPEC-0007; REQ-032 part c, the author rule)

Date: 2026-10-24 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0085. The paths: `docs/specs/0021-when-a-fix-list-verdict-s-only-item-is-the-final-commit-and.md`, `docs/specs/0007-metrics.md`.

1. **SPEC-0021 rule 5, listed verdict authors.** Add: when two or more verdict authors are listed, a verdict by the pull request's own author is not a verdict (SPEC-0025 rule 4): it clears nothing,
   covers nothing and is not a review round. `check_final_clearance.py` takes `--author LOGIN` (the workflow passes the pull request author's login); the metrics and the facts read the login from the pull request
   record. With one listed author nothing changes.
2. **SPEC-0007 rule 5 (`review_rounds`).** Add: a `Verdict: fix list` comment by the pull request's own author does not count when two or more verdict authors are listed.

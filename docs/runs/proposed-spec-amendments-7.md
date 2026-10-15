# Proposed spec amendments 7 (SPEC-0003)

Date: 2026-10-15 (from `date -u`). Found while implementing SPEC-0003 (ADR-0011, PR #22). Approved specs change only
through a proposal like this one (principle 6). This is Q-K2-20 of PR #22; the maintainers ruled that the tests move.

## SPEC-0003 (`docs/specs/0003-reviewer-agent.md`)

1. **Rule 18, where the fixtures and tests live.** Now: "A builder in `tests/kit_dev/` creates tiny git
   repositories ..." and, in the Tests section, `tests/kit_dev/test_review_context.py`,
   `tests/kit_dev/test_review_report.py`, `tests/kit_dev/test_reviewer_definition.py` and the footer tests in
   `tests/kit_dev/test_review_report.py`. Proposed: the builder is `tests/kit/review_fixtures.py` and the three test
   files are `tests/kit/test_review_context.py`, `tests/kit/test_review_report.py` and
   `tests/kit/test_reviewer_definition.py`. Reason: `tests/kit/` is installed, so the installed scripts ship with the
   tests of the checks (principle 4); `tests/kit_dev/` is not installed. The kit-only wiring tests (manifest,
   REQ-013 in this repository, kit version, installed layout) stay in `tests/kit_dev/test_reviewer_wiring.py`.

## Status

Applied 2026-10-15 on maintainers' instruction (final commit of PR #22). SPEC-0003 rule 18 and its Tests section
name `tests/kit/`; nothing else in the spec changed.

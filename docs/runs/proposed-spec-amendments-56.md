# Proposed spec amendments 56 (SPEC-0032; REQ-040)

Date: 2026-10-25 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Applied by ADR-0116. The path: `docs/specs/0032-github-events-label-each-pr-people-approve-specs-a-red-branch-stops-work.md`.

1. **SPEC-0032, a draft gets no review label.** The router gives a draft pull request no review label: `agk:review` is set only on a pull request marked ready for review, and `session.py queue --role conductor` skips drafts, so that unfinished work is not listed for review (SPEC-0033 rule 11, the verdict on its intake). The router and `queue` are built by the builds of SPEC-0032; this build adds the sentence to that spec only.

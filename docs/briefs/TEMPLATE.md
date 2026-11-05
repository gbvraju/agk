# Brief: Title

## Rules block

Operating rules that apply to every item (cite constitution/principles.md by number).

A test never pins its own ADR's status: a test of an ADR that the same pull request adds accepts Proposed or Accepted.

## Items

### Item 1 — Title

- Advances: REQ-nnn
- Scope: paths allowed to change
- Acceptance: observable results
- Branch: chore/short-name
- Size: S|M|L
- Reserved: ADR-nnnn and amendment number <n> (for each spec amendment the item adds), both reserved in the brief's field note
- Expected: <low>-<high> hours

## Report format

The PR body for each item contains:

- Advances: REQ-nnn
- Build-state row: Date | Change | REQs
- Decisions taken: one line each, with the brief section it came from
- Covered-by: ADR-nnnn, for a build of an Approved spec whose requirement's Accepted ADR names every
  protected class the build changes (in backticks); then the build writes no ADR. It writes one when it changes a
  decision of its spec or of that ADR, and always for `constitution/`, `config/reviewers.yaml`, a
  workflow, the ruleset or `.github/CODEOWNERS` (session rule 36, ADR-0271)
- Brief: <path>#<item>, with the item's Size: and Expected: lines copied unchanged
- Questions: the Q list
- Verified: commands run and their results, verbatim counts

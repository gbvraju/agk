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

The study lines, in the form `check_brief.py --root` reads (brief #1813): `Impact:` alone, its five lines in this
order, then `Wiring:`, `Prior:` and `Class:`. Replace each `(verify)` text; a line left as it is warns.

Impact:
Speed: (verify) for the person to state
Quality: (verify) for the person to state
GitHub: (verify) for the person to state
Cost: (verify) for the person to state
Tests: (verify) for the person to state
Wiring: none: (verify) for the person to state
Prior: none: (verify) for the person to state; brief_study.py lists the candidates
Class: (verify) for the person to state; seen 0 (verify)

<!-- One example each (each line is `<name>: <text>` or `<name>: none: <reason>`):
- Impact: e.g. the line alone, followed by the five lines below in this order
- Speed: e.g. about 10 minutes more per brief for its writer (measured on the next five briefs)
- Quality: e.g. a missed earlier decision fails on the brief, not after the build
- GitHub: e.g. none: no workflow, check, label or API call changes
- Cost: e.g. none for Actions: the check is file-only in the existing job
- Tests: e.g. one new test file; no change to the selection or the full run
- Wiring: e.g. scripts/agk/check_brief.py:main called by skills/brief/SKILL.md (or none: <reason>)
- Prior: e.g. ADR-0650 (Accepted), amendment 186 (or none: <what was searched>)
- Class: e.g. a check broken by a script that prints before utf8_output; seen 2 times (#1581, #1627);
  seen above 0 needs an Answers item headed **The class stays closed.** naming its guard
-->

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

# ADR-0583: Two standing owner rulings on size and the rule budget

- Status: Proposed
- Date: 2026-11-16
- Deciders: maintainers (the owner's standing decisions)
- Related: brief #1385, ADR-0310, plan #661
- Requirements: REQ-037

## Context

On 2026-11-15 and 2026-11-16 the conductor asked the owner the same two questions on nearly every steward and kit
pull request: a size over the brief's `Plan:` guide (#1326, #1332, #1333, #1348, #1349, #1352, #1356, #1361), and
an instruction file's word count over its `config/rule-budget.txt` line (ADR-0310). The owner accepted every one,
and each acceptance parked a reviewed pull request. The owner's word (2026-11-16 05:35 IST, co-owner chat, quoted
as data): "Go ahead", in answer to the recommendation, quoted: "Post the two standing rulings: oversize accepted
when the review is clean and under 3x budget; role files may grow 10% without a ruling."

## Decision

1. Size: a pull request whose changed lines, tests excluded, are at most three times its brief's size guide (300
   when the brief gives none), and whose latest verdict names no finding, is accepted without an owner question; the
   verdict says `Size: <n> of <guide>, accepted by standing ruling (ADR-0583)`.
2. Rule budget: an instruction file's word count may rise by at most ten percent over its baseline in one pull
   request with no owner ruling, when its count of rule lines does not rise; the pull request raises the baseline and
   its body says `Rule budget: <file> <old> to <new> words, standing ruling (ADR-0583)`.
3. Above either limit, with a finding or with a new rule line, the owner is asked as before. Protected-path ADRs,
   spec approvals and release merges stay the owner's. The owner withdraws either ruling by a later ADR; each
   project's owner keeps or withdraws them by its own ADR.

`scripts/agk/rules.py` states both limits as `size_ruling` and `budget_ruling`, which the tests check; the
conductor's role file names them in its verdict steps. `rules.py budget --check` is unchanged: a raise still lands
in the baseline in the same pull request. This pull request is the first use of ruling 2: the conductor's role
file goes from 4533 to 4662 words (2.8 percent) with 37 rule lines as before, so its baseline line and the fixed cap
of `tests/kit/test_conductor_playbook_evidence.py` (brief #666: below 4538) are raised to match.

Protected path classes changed: `.claude/` (`agents/conductor.md`), `config/` (`rule-budget.txt`), `scripts/agk/`
(`rules.py`), `tests/kit/` (`test_standing_rulings.py`, `test_conductor_playbook_evidence.py`) and `docs/adr/` (this file).

## Consequences

A clean pull request within both limits is cleared without waiting for the owner; the size and budget lines make each
use of a ruling visible in the verdict or the body. A tenfold oversize or a new rule still reaches the owner.

# ADR-0486: The guide says how a team of four works one repository

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: ADR-0330, ADR-0368, brief #1145, plan #661
- Requirements: REQ-039

## Context

On 2026-11-13 (IST) the owner asked how four people on four laptops, each running two or three builders, work one
repository with AGK, and asked for the answer in the guide (brief #1145). `docs/guides/getting-started.md` described one
person on one machine. The code already coordinates through GitHub: `claim` writes one `taken:` comment and refuses a
brief another session holds, `session.py plan` caps starts by `max_builders` across the whole repository, `resume`
continues a pull request from any machine, and one conductor holds the lease (ADR-0330).

## Decision

1. The guide gains the section `Working as a team`, and `tests/kit/test_guide_team.py` reads it and runs two claims of
   one brief by two session names against a `gh` stub.
2. No code changes: the test shows `claim` already leaves one `taken:` holder.
3. `max_builders` stays 6; the owner rules on 12 for a team of four (Q-1145-1).

Protected path classes changed: `tests/kit/` (`test_guide_team.py`).

## Consequences

A team has one page to follow. The guide names a protected setting the owner changes by an ADR.

## Residual

- 2026-11-12: none known; `max_builders` of 12 waits for the owner's ruling on Q-1145-1 (due 2027-01-31).

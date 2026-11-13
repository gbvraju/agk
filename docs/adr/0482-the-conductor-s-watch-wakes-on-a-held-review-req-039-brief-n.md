# ADR-0482: The conductor's watch wakes on a held review

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: ADR-0388, ADR-0402, ADR-0475, brief #854, brief #1125, plan #661
- Requirements: REQ-039

## Context

`conductor.py watch` ended only on a new `Question:`, `Report:` or owner's answer created after `--since`, on a green
label line, or after about 5 minutes with `tick` and builder stalls. A report that lands while the conductor is busy
reviewing falls before the next watch's `--since` and wakes nothing. `held_verdict_line` (brief #854, ADR-0388) already
finds a ready, green head that has waited `HELD_MINUTES` (15) with no verdict, but only `sweep` prints it, and the
conductor runs `sweep` only on a notification. On 2026-11-12 #1119 and #1115 waited about 38 and 35 minutes; `sweep` at
15:31Z printed `HELD VERDICT #1119` and `HELD VERDICT #1115` and a person restarted both builders.

## Decision

1. When a poll of `watch` finds no new line, `held_lines` returns the `held_verdict_line` of each open, non-draft pull
   request, with the reads `sweep` already makes, and `watch` prints them and returns 0 the way it prints new lines.
2. The check runs at most once per `HELD_EVERY` (300 seconds), across watches: its time is kept in the file `agk/held`
   of the checkout's git directory (beside the lease mark, never tracked) and is written before the reads, so a failed
   read does not make the next check come sooner. Without a git directory there is no check.
3. The same file keeps when each held pull request was last returned; one is returned again only after a further
   `HELD_MINUTES` without a verdict. A pull request that is no longer held loses its mark.
4. No new setting or label; `sweep`, `held_verdict_line` and `HELD_MINUTES` are unchanged, and so is
   `.claude/agents/conductor.md`.

Protected path classes changed: `scripts/agk/` (`conductor.py`) and `tests/kit/` (`test_conductor_held_wake.py`).

## Consequences

A ready pull request whose report was missed is reviewed on the conductor's next wake, at the latest about 20 minutes
after its report, without a person restarting its builder. The watch makes at most one extra pass of reads per 5 minutes
(the open pull requests, the comments and checks of each ready one), and none while new lines keep arriving.

## Residual

- 2026-11-12: two conductor checkouts of one repository keep separate marks, so each may return the same held pull
  request once; the lease allows one live conductor (due 2027-01-31).

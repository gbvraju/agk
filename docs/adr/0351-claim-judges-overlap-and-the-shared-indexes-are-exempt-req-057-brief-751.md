# ADR-0351: Claim judges overlap as next and plan do, and the shared indexes are exempt (REQ-057, brief 751)

- Status: Accepted
- Date: 2026-11-08
- Deciders: maintainers
- Related: ADR-0325, ADR-0339, ADR-0189, ADR-0195, SPEC-0050, SPEC-0034
- Requirements: REQ-057

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

SPEC-0050 (Approved) rules 2 to 4 say that `next`, `plan` and `claim` judge overlap in one function,
that `claim` refuses an overlapping brief with the same line and posts nothing, and that the shared
indexes of `[flow] shared_indexes` never make an overlap. Its build (c) is brief #751; build (b),
the re-prove hold, merged as #731, so the exemption lands after the hold (Q-S0050-3). The
requirement's ADR, ADR-0325, is still `Proposed`, so this build cannot use a `Covered-by:` line
(session rule 36) and writes the ADR the brief reserved. It changes the behaviour SPEC-0034 rule 3
states, proposed in `docs/runs/proposed-spec-amendments-138.md`.

## Decision

1. **The setting.** `session_plan.shared_indexes` reads `[flow] shared_indexes`, default
   `SHARED_INDEXES` (the five paths of rule 3). A set list replaces the default; an empty list
   exempts nothing. A value that is not a list of non-empty strings, or an entry with a wildcard
   or ending in `/` (exact paths only, Q-S0050-2), is refused with
   `setting: flow.shared_indexes must be a list of exact repository paths`, never the value.
2. **The one list.** `session_plan.exempt` returns the shared-mechanical patterns and the shared
   indexes. `next` (with and without `--take`), `plan`'s waves and `claim` pass it to
   `running_conflict` and `clash`; no second matcher is written (rule 2). A shared index still
   counts for `reprove_files` and the guarded merge's hold, which read no exemption.
3. **The refusal.** `session.claim` asks `claim_overlap` just before it would post the take (a
   `gate` of `session.take`), after the take checks of today. It reads the open briefs and pull
   requests as `next` does, frees stale claims as `next` does, and refuses with
   `skip #<n>: <wait_text>`, exit 1, posting nothing. Another build of the same brief is not a
   rival. A read that fails stops the claim (`FAIL`, exit 2) and never passes as no overlap. The
   survey is reused for the numbers the claim reserves.

## Consequences

An `Assign:` taken with `claim` can no longer start work that overlaps running work, and intakes
and builds that share only an index may run beside each other; the second to merge re-proves
(SPEC-0050 rule 6). `claim` reads the open briefs on every claim, as `next` does.

## Residual

- 2026-11-08: `session.py demand` still counts with its older `overlap` reading, without the
  exemption, and `plan`'s safe merge set still counts a shared index as shared; rule 4 names
  neither (due 2026-12-31).

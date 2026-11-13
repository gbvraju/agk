# ADR-0479: A brief's size limits its code paths

- Status: Accepted
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0030, SPEC-0043, amendment 168, brief #1121, plan #661
- Requirements: REQ-039

## Context

A brief's `Size:` line was checked only for its shape, so a brief could name more code than its size and its builder
found out at review: brief #1093, filed as `Size: M` with 8 code paths in `Touches:`, became pull request #1106 with 1,107
changed lines, against about 600 by SPEC-0043 rule 27. Of the last 100 briefs, 4 name more code paths than the limits
below and 96 do not (brief #1121).

## Decision

1. Amendment 168 of SPEC-0030 rule 4 (`docs/runs/proposed-spec-amendments-168.md`): a code path is a `Touches:` entry
   outside `tests/`, `docs/`, `changelog.d/` and `kit/hashes.json`; `Size: S` allows at most 3 and `Size: M` at most 6;
   a `Broad:` line lifts the limit; `Size: L` is refused for a brief with a `Wave:` line.
2. `session.py` `brief_problems` applies it, so `check_brief.py`, `session.py next` and `session.py plan` refuse the same
   way; the refusal names the rule and the counts, never a value of a setting.
3. `[flow] brief_code_paths = { S = 3, M = 6 }` in `agk.toml` sets the limits, read by `config.brief_code_paths`, those
   values by default; an invalid table is refused naming `setting: flow.brief_code_paths`.

## Consequences

An oversized build is split when its brief is filed, before a builder starts. Briefs already taken or with an open pull
request are not judged again. Protected path classes changed: `scripts/agk/` (`session.py`, `config.py`,
`check_brief.py`), `tests/kit/` (`test_check_brief.py`) and `agk.toml` (the setting).

## Residual

- 2026-11-12: a code path counts `Touches:` entries, not lines; a glob counts as one entry, so a brief can still grow
  past about 600 lines within its limit. The conductor's review under SPEC-0043 rule 27 stays the backstop (due
  2026-12-31).

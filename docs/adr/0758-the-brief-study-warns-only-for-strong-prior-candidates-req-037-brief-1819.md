# ADR-0758: The brief study warns only for the earlier decisions most likely to matter, at most ten (REQ-037)

- Status: Proposed
- Date: 2026-11-23
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1819, ADR-0752 (brief #1800), brief #1813, brief #1815, plan #661
- Requirements: REQ-037

Protected classes: `scripts/agk/`, `skills/`, `tests/kit/`

## Context

ADR-0752 decision 4 warns for every Accepted ADR whose whole text names a search term, including the bare file name
of a touched `.py` file. Almost every old ADR mentions `session.py` or `check_brief.py` somewhere, so the filed briefs
drew 5 to 163 warnings each (#1815 163, #1800 134 on main at 796245c2), and writers cleared them by listing about 150
ADRs in `Prior:` as "read and not of this kind". The owner's word (2026-11-23, the steward chat, quoted as data): "Yes,
brief trimming the Prior warnings".

## Decision

1. A hit is `strong` when a full code path (of `Touches:` or a `Wiring:` file) or a `Wiring:` `<module>.<function>`
   stands in the record's header (every line before the first `## `) or its `## Decision` section; a record with no
   `## Decision` heading is read whole. A hit only by a bare file name, or only in other sections, is `weak`.
2. `check_brief.py --root` warns for the strong Accepted ADRs that `Prior:` leaves out, ranked by the distinct strong
   terms they name, then the newer number, at most `brief_study.PRIOR_WARNINGS` (10, one constant, not a setting:
   Q-F11-1), followed by one line `study: Prior: <n> more candidates not warned; brief_study.py <file> --root . lists
   them` when more remain. Weak ADRs are never warned; a `Prior:` may cite one. Open briefs that meet `Touches:` stay
   warned, all of them; amendments stay printed, not warned (ADR-0752 decision 4). A warning stays a warning on any
   day, as ADR-0752 decided.
3. `brief_study.py FILE --root DIR` still prints every candidate, each line ending `strong` or `weak`: the strong
   records ranked first, then the open briefs, then the weak records.
4. The brief skill and `docs/briefs/TEMPLATE.md` say that `Prior:` names the records of the same kind, with why, and
   never lists records read and found unrelated.
5. Path classes changed: `scripts/agk/` (`brief_study.py`), `skills/` (the brief skill) and `tests/kit/` (the two
   study tests, with the guard that 40 weak mentions give no ADR warning). No setting is added; `review_mode`,
   `pr_mode`, `execution` and personal mode read the same warnings from the same function.

## Consequences

A filed brief shows at most ten ADR warnings (measured after on the same bodies: #1815, #1800, #1813 and #1814 ten
each with a `more` line, #1812 9, #1809 3, #1811 0). An ADR that decided a rule on a touched file in its Context only
is no longer warned, only printed as `weak`; the writer still reads the full list.

## Residual

The briefs filed with long `Prior:` lines (#1813, #1814, #1815) are left as they are (Q-F11-2, conservative reading).

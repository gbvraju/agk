# Proposed spec amendments 256 (SPEC-0021, SPEC-0039; REQ-028)

Date: 2026-11-26 (from `date -u`). Approved specs change only through a proposal like this one (principle 6). Written for
ADR-0827 (brief #2001), which stays `Proposed` for the maintainers' decision. The paths:
`docs/specs/0021-when-a-fix-list-verdict-s-only-item-is-the-final-commit-and.md` (rules 1, 3a and 9) and
`docs/specs/0039-the-conductor-merges-a-cleared-pull-request-through-one-guarded-command.md` (rule 3). Amendment 253 was
the newest on main and brief #2002 names 254 and 255, so this is 256 (Q-EF-1). This file proposes the lines and does not
edit the specs. They are applied word for word, on a person's `Approve: SPEC-0021` and `Approve: SPEC-0039`; no session
posts them.

## Why

Of 89 fix lists on the 30 newest merged pull requests, 40 had no numbered item, 37 of them only ADR acceptance `Final:`
lines; each woke the builder for a no-op `Report:` and 9 were reviewed a second time (brief #2001's measurement).

## Items

1. **SPEC-0021 rule 1, the covered fix list.** After "the old path (a `Verdict: cleared <sha>`) applies." insert "A
   `Verdict: cleared <sha>` with the full 40-character head whose every `Final:` line is
   `docs/adr/<file> Proposed -> Accepted` covers the same way (amendment 256); a cleared verdict with any other `Final:`
   line, or on a shorter sha, covers nothing and its `Final:` line cannot be read."
   Class: behaviour
2. **SPEC-0021 rule 3a, the acceptance.** In rule 3a, after "brief 557). When the latest covered fix list" insert " or cleared verdict (rule 1,
   amendment 256)".
   Class: behaviour
3. **SPEC-0021 rule 9, the verdict form.** After "A verdict that also has other items is written as today, without
   `Final:` lines." insert "A verdict with nothing to fix is `Verdict: cleared <head>`, carrying any rule 3a `Final:`
   lines on the full head; the conductor's check refuses, before it is posted, a fix list with no numbered item and no
   `Final:` line, or whose only `Final:` lines accept ADRs, and still reads one already posted (amendment 256)."
   Class: behaviour
4. **SPEC-0039 rule 3, a trusted verdict.** After "with nothing before or after on that line." insert " Its body may
   carry the `Final:` lines of an ADR acceptance (SPEC-0021 rule 3a, amendment 256), which the command records as it
   merges."
   Class: behaviour

No other rule changes.

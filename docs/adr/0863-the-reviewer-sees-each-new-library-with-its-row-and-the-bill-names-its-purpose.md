# ADR-0863: The reviewer sees each new library with its row, and the bill names its purpose

- Status: Proposed
- Date: 2026-11-28
- Deciders: maintainers (the owner's yes on brief #2073, 2026-11-27T19:43:53Z; amendment 260 approved on #2018,
  comment 7227145482)
- Related: ADR-0834, ADR-0867, ADR-0430, ADR-0431, ADR-0370, ADR-0074, ADR-0294, ADR-0828, SPEC-0076, SPEC-0054,
  SPEC-0023, REQ-083, brief #2073, plan #661
- Requirements: REQ-083

Protected classes: `scripts/agk/`, `tests/kit/`, `agk.toml`

## Context

SPEC-0076 (Approved, ADR-0834) rule 15 build (f) asks for the fresh reviewer's bundle and the checklist wording for a
new part row, and the bill's purpose property of amendment 260. On main at 9b6ab96 a dependency added to
`package.json` reaches the gating reviewer only as a diff hunk under `review_diff_cap`, with no record row beside it,
and `grep -c agk:purpose scripts/agk/sbom.py` gives `0`. Build (d) (ADR-0867) gave the record's reader,
`gates/parts.sections`.

## Decision

1. **The bundle's Parts section.** `review_bundle.parts_lines(root, base)` adds `## Parts` after the review context
   and before `## Brief`. Per runtime of `pins.runtimes_of` whose build file changed since the merge base, each
   direct dependency (`pins.direct`, read one npm group at a time) added, removed, at another version or moved
   between groups is one line `- <build file>: <name> <base> -> <head>` (`none` absent, `unpinned` not exact, the
   groups in brackets on a move), then its rows of `docs/parts.md` at the head fenced, or `- no row in docs/parts.md`;
   with no record each line ends `: no parts record`. Each record row added or edited whose part no build file line
   showed follows as `- docs/parts.md: <part> <version>` and the row. A build file that cannot be read is
   `- <build file>: cannot be read`. With nothing changed: `- no build file or parts record changed`; with no stack:
   `- not run parts: no stack chosen`; a refused `[parts]` table: `- not run parts: the [parts] table is refused
   (setting: parts.<key>)`. The section is cut at `review_other_cap` with the `[truncated: n lines omitted]` marker.
   `review_context.assemble` is unchanged, so the conductor's own context is the same.
2. **The bill's purpose (amendment 260).** `sbom.purposes(root, commit, stack)` reads `docs/parts.md` at the commit
   through `parts.sections`: with two runtimes each class reads its own `## <runtime>` section, with one runtime every
   row is that runtime's, and with no stack the `python` class's; `stdlib` rows name no component. `entry` gains
   `purpose`, one `agk:purpose` per need, sorted, after `agk:class` and `agk:pin`; `python_components` and
   `lock_components` pass it. A component no row names carries none. A record with no table of the nine columns, or
   not UTF-8, refuses the bill as `docs/parts.md cannot be parsed at the commit (rule 2)`. Without a record the bill
   is byte for byte the same. `well_formed` allows `agk:purpose`; any other name is still refused.
3. **The amendment.** Amendment 260's two items are applied to SPEC-0054 rules 2 and 3 word for word, and
   `docs/runs/proposed-spec-amendments-260.md` records it, on the maintainer's answer on #2018.
4. **The checklist stays.** No catch-log row records a library added without its reason (searched by GET, `Q-PF-2`),
   so `config/review-checklist.md` item 8 is unchanged (SPEC-0023 rule 5). `Q-2073-1` is answered on #2089 (comment
   7234429030): a spec rule naming the wording is not that record; the wording waits for a catch-log row.

## Consequences

The gating reviewer sees why each new library is there, or that no reason was written. The bill names which need
each component serves. No workflow, ruleset, required check, label, `agk.mk` or `governance_map.CHECKS` changes, and
no baseline of `config/rule-budget.txt` rises.

## Residual

Checklist item 8's wording waits for a catch-log row of a library added without its reason, then goes in its own
change (`Q-2073-1`, 2026-11-28). Other stacks wait for build (h).

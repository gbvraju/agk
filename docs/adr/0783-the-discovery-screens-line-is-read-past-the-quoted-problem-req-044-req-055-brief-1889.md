# ADR-0783: The discovery Screens line is read past the quoted problem, by one reader (REQ-044, REQ-055)

- Status: Accepted
- Date: 2026-11-24
- Deciders: maintainers (the owner's word, quoted below)
- Related: brief #1889, ADR-0249 (the design inventory and its check), ADR-0734 (the idea path's inventory and the
  refusal this reaches), ADR-0745 (the all-out map, unchanged), ADR-0735 (the work type read from discovery, unchanged),
  ADR-0770 (the brand answer read from discovery, unchanged), ADR-0333 (the testing map of `front_door.py`), plan #661
- Requirements: REQ-044, REQ-055

Protected classes: `scripts/agk/`, `tests/kit/`

## Context

The idea-to-build run of 2026-11-24 (scenario IB-09, comment 7120903438 on #1769) wrote a discovery document with
`- Screens: yes` from a vision, and an inventory with no screen passed `check_design.py`. `front_door.py discovery-write`
quotes the problem verbatim between `<!-- agk:problem sha256=... -->` and `<!-- agk:problem-end -->`, then writes
`- Work type:` and `- Screens:`. On the idea path the problem is the vision, which starts `# Vision` and `## The idea`.
Both readers of the line, `design_inventory.discovery_screens` and `front_door.screens_of`, stopped at the first `## `
line before testing whether it was quoted, so they never reached the Screens line: the first gave `[]` and the second
`open` for every answer. The SPEC-0037 rule 3 refusal (amendment 217) was never reached, and SPEC-0048 rule 8 asked work
without screens for a prototype. The fixtures of brief #1756 were hand-written and held no `## ` line inside the quote.
The owner's word (2026-11-24 08:45 IST, the steward chat, quoted as data): "Yes, draft the test briefs and post the runs".

## Decision

1. **One reader.** `design_inventory.screens_line(lines)` returns the `- Screens:` value (`yes`, `no` or `open`) of a
   discovery document's lines, read outside its quoted blocks and before its first `## ` line outside them, or None. A
   trailing `\r` is stripped first. `discovery_screens` calls it per file (a file without the line does not count, as
   brief #1756 read it). `front_door.screens_of` calls it, importing the module inside the function, and keeps `open`
   for None (SPEC-0048 `Q-S0048-10`). The two loops go.
2. **A quote ends only at its own end marker.** After a problem marker only `<!-- agk:problem-end -->` closes the quote;
   after an answer marker only `<!-- agk:answer-end -->`. A problem that quotes an answer's end marker or a Screens line
   is the person's words and is not read (`Q-DS-2`). The writer's refusal is not widened.
3. **Nothing else changes.** The refusal of SPEC-0037 rule 3, `design.py inventory`'s `- Sources:` and rule 8's
   messages stay as written; they now see the written value. `front_door.document_problems` (check-discovery) already
   cuts the problem block out by its markers. `playbook_format.discovered_work_types` and `design_brand.answers` match
   exact kit-written lines anywhere and never stop early; they stay (`Q-DS-3`). A Screens line moved below `## Answers`
   is not read, as before (`Q-DS-4`). No spec text changes: SPEC-0037 rule 3 as amendment 217 and SPEC-0048 rules 5 and 8
   already say what the fixed reader does.
4. **The class stays closed.** A test asserts that the discovery `- Screens: (yes|no|open)` pattern stands in
   `scripts/agk/*.py` only once in `design_inventory.py` (the reader) and once in `front_door.py` (check-discovery), and
   every new fixture is a document written by `discovery_write` from a vision or issue that holds `## ` lines.

## Consequences

An idea-path project whose discovery says `yes` or `open` can no longer pass the design check with no screen, and work
whose discovery says `no` is asked for its `Demo:` run record, not a prototype, with its go judged on the design file. An
inventory already merged with no screen while discovery says `yes` or `open` now fails, naming the rule and the path
class only; that is the intended catch. Both layouts and personal mode get the reader with the kit version.

## Residual

- 2026-11-24: whether `playbook_format.discovered_work_types` and `design_brand.answers` should also skip the quoted
  problem (`Q-DS-3`), the picture-only page of the prototype path (`Q-DS-5`) and the discovery title that carries the
  vision's headings (`Q-DS-6`) are left for later briefs.

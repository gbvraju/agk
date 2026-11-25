# ADR-0803: The discovery record holds assumptions, risks and readiness, and the design waits on it

- Status: Proposed
- Date: 2026-11-25
- Deciders: maintainers
- Related: SPEC-0073, SPEC-0048, SPEC-0037, SPEC-0059, ADR-0801, ADR-0802, ADR-0793, amendment 235, brief #1938, brief #1934, plan #661
- Requirements: REQ-080

Protected classes: `scripts/agk/`, `skills/`, `docs/specs/`, `tests/kit/`

## Context

SPEC-0073 (Approved) rule 15 build (c) follows build (b) (ADR-0802, merged as #1946). On the default branch at 1fb8181,
`grill.py record` keeps each grill answer in the answers file's `grill` list and `grill.py ready` prints the readiness
line, but `front_door.py discovery-write` reads only `answers`, `points`, `work_type` and `screens`, so no grill answer
reaches the discovery document; `check-discovery` knows only `## Answers` and `## Open points`; `front_door.py status`
prints the phase alone; and `check_design.py` (the governance step `design`) returns `ok design (no design record)` on a
tree that holds only `docs/design/architecture/<slug>.md`. The owner approved amendment 235 on #1920 (`Maintainer answer:
amendment 235 approved`, 2026-11-25 10:25 UTC); its five items are SPEC-0048's side of this build.

## Decision

1. **The writer.** `discovery_write` appends `## Assumptions`, `## Risks` and `## Readiness` after `## Open points` only
   when the answers file has a non-empty `grill` list; without one the document is written byte for byte as before.
   - `## Assumptions`: for each grill id with a row, in the composed order of `grill.py questions`, one bullet
     `- A-<n>: <id>: "<claim>" (stated|assumption|open)` (an `open` row with no words reads `- A-<n>: <id>: (open)`),
     its last status row counting, followed by indented lines `  Test: <test>` for an assumption, `  Source: <source>`
     when given, `  accepted recommendation (<where>, <UTC time>)` for a recorded yes and `  Risk accepted: <id> (<UTC
     time>)` for an accepted risk. A risk accepted on an id with no status row gives that id an `open` bullet.
   - `## Risks`: `- R-<n>: <risk>; first sign: <sign>; owner: <who>` from the answers file's `risks` list, or `- none`.
   - `## Readiness`: the one line `grill.readiness` prints on the same answers file.
   Each critical grill item that is not settled and has no accepted risk gets a `- D-<n>: \`<id>\` is open` point in
   `## Open points`, after the open answers' points and before the person's points. The composition is the project's
   (`grill.composed(root, None)`: the declared work type's playbook, else `default.toml` alone), the one `grill.py ready`
   reads by default. `guard_problems` runs on the whole text as before.
2. **The checker.** `front_door.quality_problems(rel, text, root)` is called by `check_discovery` after
   `document_problems`, only when a document has any of the three sections. Each failure names rule 7, the section and
   the file, never a value: a section present without the other two; a line of a section not of rule 7's form; `A-<n>`
   or `R-<n>` numbers not 1, 2, 3 ... in order; an `A-<n>` id outside the composed grill ids; an `assumption` with no
   `Test:`; an `open` critical item with no `D-<n>` point and no accepted risk; a `## Readiness` that is not one line of
   rule 7's form, whose critical total is not the composed playbook's or whose settled count exceeds it; a risk id in the
   readiness line with no `A-<n>` that names it. `document_problems`, `phase_of`, `answer_lines` and
   `check_acceptance.py` are unchanged (SPEC-0073 rule 4).
3. **Status.** `front_door.py status` prints, under each name whose discovery document has `## Readiness`, the line
   `  readiness: <the readiness line>`, and, while `[quality] grill_hold` is true and a critical item is open with no
   accepted risk, `  held at the design: <ids>`. A document without the section prints as before.
4. **The hold.** `check_design.py cmd_check` first asks `front_door.design_holds(root)`: for each
   `docs/design/architecture/<slug>.md` whose `docs/discovery/<slug>.md` has a `## Readiness` line with fewer settled
   than total critical items, it fails `SPEC-0073 rule 6: docs/design/architecture/<slug>.md is held: its discovery has
   an open critical item (setting: quality.grill_hold)` while `grill_hold` is true. This runs before the `no design
   record` return. A discovery document with no `## Readiness`, a design with no discovery document of its slug and
   `grill_hold = false` hold nothing; a refused `[quality]` table fails naming the setting, read only when a design has
   such a discovery document. Discovery's own merge is never held.
5. **The risks.** `grill.py record --answers FILE --id ID --risk TEXT --sign TEXT --owner WHO` appends `{id, risk, sign,
   owner}` to the answers file's `risks` list; each value is one line, non-empty and passed by the data guard. The grill
   skill records each pre-mortem risk this way and as one `Risk:` steward memory entry; the document is the source of
   truth.
6. **The amendment.** Amendment 235 items 1 to 5 are applied word for word to SPEC-0048 rules 4 to 7 and 13.

## Consequences

A design cannot pass the governance step `design` while its idea's critical questions are open, unless the person has
accepted the risk; readiness is visible in `front_door.py status`. Every existing discovery document, answers file and
design reads as before. No workflow, label, required check, `agk.mk` recipe or `governance_map.CHECKS` changes.

## Residual

- A later grill on an existing document is not appended: `discovery_write` still refuses an existing file (`Q-73C-2`).
- Who may accept a risk in team mode is build (d)'s.

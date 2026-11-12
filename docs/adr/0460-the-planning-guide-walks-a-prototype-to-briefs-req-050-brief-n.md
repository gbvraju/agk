# ADR-0460: The planning guide walks a prototype to briefs, and amendment 163 is in the spec texts

- Status: Proposed
- Date: 2026-11-12
- Deciders: maintainers
- Related: SPEC-0043, SPEC-0037, ADR-0269, ADR-0454, ADR-0455, ADR-0456, ADR-0457, ADR-0458, ADR-0459, ADR-0461, amendment 163, amendment 115, brief #1079, plan #661
- Requirements: REQ-050, REQ-044

## Context

SPEC-0043 (Approved, REQ-050, ADR-0269) ends its plan path with build (j), the guide and a recorded walk (rule 26 and
rule 27). Amendment 163 (ADR-0454, brief #1073) ordered the path for a customer's prototype: (b) the sources, then (c)
the draft, (d) the trace and (k) the prototype source, then (i) `publish`, then (j). Those builds are on the default
branch (`check_plan.py`, `plan_intake.py` with `validate`, `states`, `render` and `publish`, `design_import.py source`,
`skills/plan-intake/`), but no page tells a person how to use them, and the amendment's text was never written into the
two specs. The owner ruled `Q-1073-2` on #1080 at 05:34Z, before it merged, so the merged amendment still reads
"`role="alert"` or `role="status"` only" where the ruling and the code read every visible text.

## Decision

1. `docs/guides/planning.md` shows the path in order: `/agk:design import`, `design_import.py source`, the documents
   under `docs/sources/`, `/agk:plan-intake` (which runs `plan_intake.py states` first), `validate`, `render`,
   `check_plan.py --trace`, the person's `Approve: plan <full head ID>` and `publish`. It opens with rule 26's honest
   limits: the rule's sentence, no estimate on this path yet (builds (e) to (h) are not built), AGK never contacts the
   customer and never reads a source the person did not provide, and the person never forwards one AGK should not read.
2. `docs/guides/reference.md` lists `render`, `publish`, `design_import.py source` and `check_plan.py` beside
   `validate` and `states`, and points to the guide.
3. `docs/runs/plan-walk-2026-11-12.md` records one walk on an invented project of `example.com` (a three-screen
   prototype of four pages and one picture page, and one product requirements document): each command and its output
   verbatim, run with the kit's scripts on a temporary project, ending with the printed `gh api` commands and then the
   coverage line `ok plan: 8 of 8 ...`. The proposals file is written by hand as the skill would write it, so the walk
   needs no model.
4. Amendment 163 is written into the texts: SPEC-0043 gains rule 2a and the additions to rules 6, 10, 11 and 27, and
   SPEC-0037 rule 13 gains the one exception. Rule 2a carries the owner's ruling on `Q-1073-2` (all text outside
   `script`, `style` and `template` elements, in document order) and names the command as built,
   `design_import.py source`, where the amendment wrote `design.py source`.
5. `tests/kit/test_guide_planning.py` holds it: the guide names each command in order and the limits, the reference
   lists the commands, the walk records each step in order, ends with an `ok plan:` line and names no host but
   `example.com`, and the spec texts carry the amendment and the ruling.

Protected path classes changed: `tests/kit/` (`test_guide_planning.py`). The guide, the walk, the specs and this ADR are
not protected; no script, workflow or installed file changes.

## Consequences

A person with a prototype and documents can follow one page, and one recorded run, from the import to the printed
milestone and brief commands, knowing what AGK will not do. Amendment 163's rules are read in the specs themselves.

## Residual

- 2026-11-12: `design_import.py source` refuses a version while any `yes` state of the inventory is uncovered (SPEC-0037
  rule 15), so `plan_intake.py states` finds a state to ask only when a kit version covers it; the guide and the walk
  describe that as built (`Q-1079-1`) (due 2026-12-31).
- 2026-11-12: the `[plan]` settings of amendment 115 item 4 are not in the reference, because build (e) has not added
  them (due 2026-12-31).
